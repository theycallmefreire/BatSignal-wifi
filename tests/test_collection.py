import subprocess
import threading
from queue import Queue
from types import SimpleNamespace

import pytest

import wifi_coleta as wifi


@pytest.mark.parametrize(
    "name,label",
    [
        ("Nome", "Sinal"),
        ("Name", "Signal"),
        ("Nombre", "Señal"),
        ("Nom", "Signal"),
        ("Name", "Signal"),
    ],
)
def test_localized_output_with_network_metadata(name, label):
    output = f"{name} : Wi-Fi\nSSID : Minha rede\nBSSID : ab:cd:ef:00:11:22\n{label} : 43%"
    assert wifi.parse_interfaces(output) == [
        wifi.WiFiReading(43, "Wi-Fi", "Minha rede", "ab:cd:ef:00:11:22")
    ]


@pytest.mark.parametrize("value", ["-1%", "101%", "abc", "50", "1.2%", "1000%"])
def test_invalid_strength_is_not_used(value):
    assert wifi.parse_interfaces(f"Name : Wi-Fi\nSignal : {value}") == []


def test_disconnected_adapter_does_not_reuse_previous_signal():
    readings = wifi.parse_interfaces(
        "Name : Connected\nSignal : 0%\nName : Disconnected\nState : disconnected"
    )
    assert readings == [wifi.WiFiReading(0, "Connected")]


def result(output, returncode=0):
    return SimpleNamespace(stdout=output.encode("oem"), returncode=returncode)


def test_multiple_interfaces_require_selection(monkeypatch):
    monkeypatch.setattr(
        wifi.subprocess,
        "run",
        lambda *a, **k: result("Name : Wi-Fi\nSignal : 20%\nName : Wi-Fi 2\nSignal : 90%"),
    )
    with pytest.raises(wifi.WiFiError, match="mais de uma"):
        wifi.get_wifi_reading()
    assert wifi.get_wifi_reading("wi-fi 2").forca == 90
    with pytest.raises(wifi.WiFiError, match="Nenhum sinal"):
        wifi.get_wifi_reading("Missing")


@pytest.mark.parametrize(
    "failure,message",
    [
        (subprocess.TimeoutExpired("netsh", 5), "demorou"),
        (FileNotFoundError(), "executar netsh"),
    ],
)
def test_command_failures_are_actionable(monkeypatch, failure, message):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(wifi.subprocess, "run", fail)
    with pytest.raises(wifi.WiFiError, match=message):
        wifi.get_wifi_reading()


def test_command_uses_timeout_without_shell(monkeypatch):
    def run(args, **kwargs):
        assert args == ["netsh", "wlan", "show", "interfaces"]
        assert kwargs["timeout"] == 5
        assert not kwargs.get("shell")
        return result("Name : Wi-Fi\nSignal : 100%")

    monkeypatch.setattr(wifi.subprocess, "run", run)
    assert wifi.get_wifi_reading().forca == 100


def test_nonzero_exit_and_missing_signal(monkeypatch):
    monkeypatch.setattr(wifi.subprocess, "run", lambda *a, **k: result("", 1))
    with pytest.raises(wifi.WiFiError, match="recusou"):
        wifi.get_wifi_reading()
    monkeypatch.setattr(wifi.subprocess, "run", lambda *a, **k: result("State : disconnected"))
    with pytest.raises(wifi.WiFiError, match="Nenhum sinal"):
        wifi.get_wifi_reading()


def test_worker_recovers_after_temporary_disconnect():
    queue, stop = Queue(), threading.Event()
    attempts = []

    def reader():
        attempts.append(1)
        if len(attempts) == 1:
            raise wifi.WiFiError("Disconnected")
        return wifi.WiFiReading(55)

    wifi.collect_samples(0.04, 0.01, stop, queue, reader)
    events = list(queue.queue)
    assert events[0] == ("error", "Disconnected")
    assert events[-1][0] == "done"
    assert events[-1][1]["samples"]
    assert not events[-1][1]["cancelled"]
    assert "timestamp" in events[-1][1]["samples"][0]


def test_cancel_interrupts_long_sampling_wait():
    queue, stop, read = Queue(), threading.Event(), threading.Event()

    def reader():
        read.set()
        return wifi.WiFiReading(55)

    worker = threading.Thread(target=wifi.collect_samples, args=(60, 30, stop, queue, reader))
    worker.start()
    assert read.wait(2)
    stop.set()
    worker.join(2)
    assert not worker.is_alive()
    assert list(queue.queue)[-1][1]["cancelled"]


def test_unexpected_worker_failure_still_finishes():
    queue = Queue()

    def reader():
        raise RuntimeError("simulated bug")

    wifi.collect_samples(1, 1, threading.Event(), queue, reader)
    assert list(queue.queue)[-1][1]["error"]
