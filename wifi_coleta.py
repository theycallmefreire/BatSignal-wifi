"""Read connected Wi-Fi interfaces without modifying network settings."""

import logging
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class WiFiError(RuntimeError):
    """An actionable collection error that can be displayed in the UI."""


@dataclass(frozen=True)
class WiFiReading:
    forca: int
    interface: str = ""
    ssid: str = ""
    bssid: str = ""

    def as_sample(self) -> dict:
        now = datetime.now().astimezone()
        return {
            "tempo": now.strftime("%H:%M:%S"),
            "timestamp": now.isoformat(timespec="seconds"),
            **asdict(self),
        }


def normalize_label(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c)
    ).strip()


def parse_interfaces(output: str) -> list[WiFiReading]:
    """Parse PT/EN/ES/FR/DE netsh output, keeping interface identities separate."""
    groups = []
    fields = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        label, value = normalize_label(label), value.strip()
        if label in {"name", "nome", "nombre", "nom"}:
            if fields:
                groups.append(fields)
            fields = {"interface": value}
        elif label in {"signal", "sinal", "senal"}:
            match = re.fullmatch(r"(\d{1,3})\s*%", value)
            if match and 0 <= int(match[1]) <= 100:
                fields["forca"] = int(match[1])
        elif label in {"ssid", "bssid", "ap bssid"}:
            fields["bssid" if label == "ap bssid" else label] = value
    if fields:
        groups.append(fields)
    return [WiFiReading(**group) for group in groups if "forca" in group]


def get_wifi_reading(interface: str | None = None, timeout: float = 5) -> WiFiReading:
    if sys.platform != "win32":
        raise WiFiError("A coleta Wi-Fi está disponível apenas no Windows.")
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            timeout=timeout,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise WiFiError("O Windows demorou a responder. Tente novamente.") from exc
    except OSError as exc:
        raise WiFiError("Não foi possível executar netsh. Verifique o serviço Wi-Fi.") from exc

    # netsh uses the Windows console code page.
    try:
        output = result.stdout.decode("utf-8-sig")
    except UnicodeDecodeError:
        output = result.stdout.decode("oem", errors="replace")
    if result.returncode:
        logger.warning("netsh failed with exit code %s", result.returncode)
        raise WiFiError(
            "O Windows recusou a consulta Wi-Fi. Verifique o serviço WLAN "
            "e as permissões de localização nas configurações do Windows."
        )
    readings = parse_interfaces(output)
    if interface:
        readings = [r for r in readings if r.interface.casefold() == interface.casefold()]
    if not readings:
        raise WiFiError(
            "Nenhum sinal disponível. Verifique a conexão Wi-Fi, as permissões "
            "de localização e o idioma de saída do netsh (PT/EN/ES/FR/DE)."
        )
    if len(readings) > 1:
        raise WiFiError(
            "Há mais de uma interface Wi-Fi conectada. Informe o nome da "
            "interface desejada no campo Interface."
        )
    return readings[0]


def get_wifi_strength():
    """Compatibility wrapper for callers that expect a percentage or None."""
    try:
        return get_wifi_reading().forca
    except WiFiError:
        return None


def collect_samples(duration, interval, stop_event, events, reader=get_wifi_reading):
    """Worker: communicate through a queue; never call Tk from this thread.

    The UI commits complete collections. Cancelled or unexpectedly failed
    collections do not replace previously stored room measurements.
    """
    samples = []
    failure = None
    try:
        if duration <= 0 or interval <= 0 or interval > duration:
            raise ValueError("Duração e intervalo inválidos.")
        deadline = time.monotonic() + duration
        next_sample = time.monotonic()
        while not stop_event.is_set() and time.monotonic() < deadline:
            try:
                reading = reader()
                if stop_event.is_set():
                    break
                sample = reading.as_sample()
                samples.append(sample)
                events.put(("sample", sample))
            except WiFiError as exc:
                events.put(("error", str(exc)))
            next_sample += interval
            # Do not issue bursts of catch-up queries after a slow response.
            next_sample = max(next_sample, time.monotonic())
            stop_event.wait(max(0, min(next_sample, deadline) - time.monotonic()))
    except Exception:
        logger.exception("Unexpected collection failure")
        failure = "Falha inesperada na coleta. Consulte o arquivo batsignal.log."
    finally:
        events.put(
            ("done", {"samples": samples, "cancelled": stop_event.is_set(), "error": failure})
        )
