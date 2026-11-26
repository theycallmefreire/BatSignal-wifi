import copy

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from openpyxl import load_workbook

import wifi_exportacao as export
from wifi_graficos import (
    comparar_mapeamentos,
    cor_sinal,
    criar_grafico_barras,
    criar_grafico_linha,
)


def test_more_than_five_rooms_and_full_signal_range(rooms):
    many = {f"Room {i}": copy.deepcopy(rooms["Sala"]) for i in range(12)}
    line = criar_grafico_linha(many)
    FigureCanvasAgg(line).draw()
    assert line.axes[0].get_ylim() == (0, 100)
    assert len(line.axes[0].lines) == 24  # readings and averages
    bars = criar_grafico_barras(many)
    FigureCanvasAgg(bars).draw()
    assert bars.axes[0].get_xlim() == (0, 100)
    assert len(bars.axes[0].patches) == 12


def test_threshold_boundaries():
    assert cor_sinal(92) == cor_sinal(0)
    assert cor_sinal(92.1) == cor_sinal(95)
    assert cor_sinal(95.1) == cor_sinal(100)
    assert len({cor_sinal(92), cor_sinal(95), cor_sinal(100)}) == 3


def test_before_after_matches_room_names_without_mutation(rooms):
    before = copy.deepcopy(rooms)
    after = {
        "Sala": [{"tempo": "12:00:00", "forca": 70}],
        "Novo": [{"tempo": "12:00:00", "forca": 1}],
    }
    assert comparar_mapeamentos(before, after) == [
        {"comodo": "Sala", "antes": 50, "depois": 70, "diferenca": 20}
    ]
    assert before == rooms
    with pytest.raises(ValueError, match="mesmo nome"):
        comparar_mapeamentos({"A": rooms["Sala"]}, {"B": rooms["Sala"]})


def test_excel_invalid_colliding_names_and_formula_like_strings(tmp_path):
    names = ["Resumo", "resumo", "A/B", "A:B", "x" * 40, "x" * 39 + "y", "=1+1", "'"]
    samples = [{"tempo": "12:00:00", "forca": 45, "ssid": '=HYPERLINK("test")'}]
    rooms = {name: samples for name in names}
    path = tmp_path / "report.xlsx"
    export.exportar_mapeamento_excel(path, rooms)
    workbook = load_workbook(path)
    assert len(workbook.sheetnames) == len(names) + 1
    assert len({n.casefold() for n in workbook.sheetnames}) == len(names) + 1
    assert all(len(n) <= 31 and not any(c in n for c in r":\/?*[]") for n in workbook.sheetnames)
    assert workbook["Resumo"].max_row == len(names) + 1
    formula_name = workbook["Resumo"].cell(8, 1)
    assert formula_name.value == "=1+1" and formula_name.data_type == "s"
    for sheet in workbook.worksheets[1:]:
        assert sheet["E2"].data_type == "s"
        assert sheet["E2"].value == '=HYPERLINK("test")'
    workbook.close()


def test_failed_export_keeps_destination(tmp_path, monkeypatch, rooms):
    target = tmp_path / "report.xlsx"
    target.write_bytes(b"original")

    def fail(*args):
        raise PermissionError("File open in Excel")

    monkeypatch.setattr(export.os, "replace", fail)
    with pytest.raises(PermissionError):
        export.exportar_mapeamento_excel(target, rooms)
    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]
