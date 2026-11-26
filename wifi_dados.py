"""Validated, atomic local survey persistence, including legacy JSON support."""

import json
import logging
import math
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app_paths import data_directory

logger = logging.getLogger(__name__)
PASTA_DADOS = data_directory()


def validar_comodos(comodos):
    if not isinstance(comodos, dict) or not comodos:
        raise ValueError("O mapeamento deve conter pelo menos um cômodo.")
    for name, samples in comodos.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Nome de cômodo inválido.")
        if not isinstance(samples, list) or not samples:
            raise ValueError(f"O cômodo '{name}' não contém medições.")
        for sample in samples:
            if not isinstance(sample, dict):
                raise ValueError(f"Medição inválida em '{name}'.")
            value = sample.get("forca")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 100
            ):
                raise ValueError(f"Sinal inválido em '{name}': esperado valor de 0 a 100.")
            if not isinstance(sample.get("tempo"), str):
                raise ValueError(f"Horário ausente em '{name}'.")
            try:
                datetime.strptime(sample["tempo"], "%H:%M:%S")
                if "timestamp" in sample:
                    datetime.fromisoformat(sample["timestamp"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Horário inválido em '{name}'.") from exc
            for field in ("ssid", "bssid", "interface"):
                if field in sample and not isinstance(sample[field], str):
                    raise ValueError(f"Campo '{field}' inválido em '{name}'.")
    return comodos


def validar_mapeamento(data):
    if not isinstance(data, dict):
        raise ValueError("O arquivo deve conter um objeto JSON.")
    if not isinstance(data.get("nome"), str) or not data["nome"].strip():
        raise ValueError("Nome do mapeamento ausente.")
    try:
        datetime.fromisoformat(data["data"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Data do mapeamento inválida.") from exc
    version = data.get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Versão do arquivo não suportada.")
    validar_comodos(data.get("comodos"))
    return data


def criar_pasta_dados():
    Path(PASTA_DADOS).mkdir(parents=True, exist_ok=True)


def gerar_nome_arquivo(nome_mapeamento):
    # Prefix also avoids Windows device names such as CON and NUL.
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome_mapeamento)
    clean = re.sub(r"\s+", "_", clean).strip(". _")[:70] or "Mapeamento"
    return f"survey_{clean}_{datetime.now():%Y-%m-%d_%H-%M-%S}_{uuid4().hex[:8]}.json"


def salvar_mapeamento(nome_mapeamento, dados_por_comodo):
    data = validar_mapeamento(
        {
            "schema_version": 2,
            "nome": nome_mapeamento,
            "data": datetime.now().astimezone().isoformat(timespec="seconds"),
            "comodos": dados_por_comodo,
        }
    )
    criar_pasta_dados()
    target = Path(PASTA_DADOS) / gerar_nome_arquivo(nome_mapeamento)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=PASTA_DADOS, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return str(target)


def carregar_mapeamento(caminho_arquivo):
    with open(caminho_arquivo, encoding="utf-8") as handle:
        return validar_mapeamento(json.load(handle))


def listar_mapeamentos():
    criar_pasta_dados()
    results = []
    for path in sorted(Path(PASTA_DADOS).glob("*.json"), reverse=True):
        try:
            data = carregar_mapeamento(path)
        except (OSError, ValueError) as exc:
            logger.warning("Skipping invalid survey %s: %s", path.name, exc)
            continue
        results.append(
            {
                "arquivo": path.name,
                "nome": data["nome"],
                "data": data["data"],
                "caminho": str(path),
                "comodos": len(data["comodos"]),
            }
        )
    return results


def deletar_mapeamento(caminho_arquivo):
    path = Path(caminho_arquivo).resolve()
    if path.parent != Path(PASTA_DADOS).resolve() or path.suffix.lower() != ".json":
        raise ValueError("Só é possível excluir mapeamentos da pasta de dados.")
    path.unlink()
    return True
