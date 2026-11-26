import json
from pathlib import Path

import pytest

import wifi_dados as data


@pytest.mark.parametrize(
    "bad",
    [
        {},
        [],
        {"Sala": []},
        {"": [{"tempo": "12:00:00", "forca": 50}]},
        {"Sala": [{"tempo": "12:00:00", "forca": True}]},
        {"Sala": [{"tempo": "12:00:00", "forca": float("nan")}]},
        {"Sala": [{"tempo": "12:00:00", "forca": 101}]},
        {"Sala": [{"tempo": "99:00:00", "forca": 50}]},
        {"Sala": [{"forca": 50}]},
        {"Sala": [{"tempo": "12:00:00", "forca": 50, "ssid": []}]},
    ],
)
def test_rejects_invalid_rooms(bad):
    with pytest.raises(ValueError):
        data.validar_comodos(bad)


def test_legacy_roundtrip_and_unique_safe_filenames(tmp_path, monkeypatch, survey):
    monkeypatch.setattr(data, "PASTA_DADOS", tmp_path)
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps(survey), encoding="utf-8")
    loaded = data.carregar_mapeamento(legacy)
    first = Path(data.salvar_mapeamento("../CON:Casa?*\\test", loaded["comodos"]))
    second = Path(data.salvar_mapeamento("../CON:Casa?*\\test", loaded["comodos"]))
    assert first.parent == tmp_path and second.parent == tmp_path
    assert first != second
    assert not any(char in first.name for char in ":?*\\/")
    assert data.carregar_mapeamento(first)["comodos"] == survey["comodos"]
    assert data.carregar_mapeamento(first)["schema_version"] == 2


def test_atomic_save_failure_preserves_existing_file(tmp_path, monkeypatch, rooms):
    monkeypatch.setattr(data, "PASTA_DADOS", tmp_path)
    existing = Path(data.salvar_mapeamento("Casa", rooms))
    original = existing.read_bytes()

    def fail(*args):
        raise OSError("disk error")

    monkeypatch.setattr(data.os, "replace", fail)
    with pytest.raises(OSError):
        data.salvar_mapeamento("Casa", rooms)
    assert existing.read_bytes() == original
    assert list(tmp_path.glob("*.tmp")) == []
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_invalid_file_does_not_hide_valid_surveys(tmp_path, monkeypatch, rooms):
    monkeypatch.setattr(data, "PASTA_DADOS", tmp_path)
    data.salvar_mapeamento("Valid", rooms)
    (tmp_path / "broken.json").write_text('{"nome":', encoding="utf-8")
    (tmp_path / "wrong_schema.json").write_text('{"nome": "Invalid"}', encoding="utf-8")
    assert [s["nome"] for s in data.listar_mapeamentos()] == ["Valid"]


def test_delete_cannot_escape_storage(tmp_path, monkeypatch):
    storage = tmp_path / "dados"
    storage.mkdir()
    monkeypatch.setattr(data, "PASTA_DADOS", storage)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        data.deletar_mapeamento(outside)
    assert outside.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 99),
        ("schema_version", True),
        ("data", "tomorrow"),
        ("nome", ""),
    ],
)
def test_invalid_survey_metadata(survey, field, value):
    survey[field] = value
    with pytest.raises(ValueError):
        data.validar_mapeamento(survey)
