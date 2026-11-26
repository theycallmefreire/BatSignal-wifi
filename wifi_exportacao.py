"""Excel export with safe sheet names and atomic file replacement."""

import os
import re
import tempfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from wifi_dados import validar_comodos


def nomes_abas(comodos):
    used = {"resumo", "history"}
    result = {}
    for room in comodos:
        base = re.sub(r"[:\\/?*\[\]\x00-\x1f]", "_", room).strip(" '") or "Comodo"
        base = base[:31]
        name, index = base, 2
        while name.casefold() in used:
            suffix = f" ({index})"
            name = base[: 31 - len(suffix)] + suffix
            index += 1
        used.add(name.casefold())
        result[room] = name
    return result


def append_values(sheet, values):
    values = [
        ILLEGAL_CHARACTERS_RE.sub("", value) if isinstance(value, str) else value
        for value in values
    ]
    sheet.append(values)
    # Treat user-controlled room names and network names as literal strings.
    for cell, value in zip(sheet[sheet.max_row], values):
        if isinstance(value, str):
            cell.data_type = "s"


def format_sheet(sheet):
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="176B98")
    for column in sheet.columns:
        width = min(50, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
        sheet.column_dimensions[get_column_letter(column[0].column)].width = width


def exportar_mapeamento_excel(caminho, dados_por_comodo):
    validar_comodos(dados_por_comodo)
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Resumo"
    append_values(summary, ["Cômodo", "Aba", "Mínimo (%)", "Máximo (%)", "Médio (%)", "Medições"])
    names = nomes_abas(dados_por_comodo)
    fields = ("tempo", "forca", "timestamp", "interface", "ssid", "bssid")
    for room, samples in dados_por_comodo.items():
        sheet = workbook.create_sheet(names[room])
        append_values(sheet, list(fields))
        for sample in samples:
            append_values(sheet, [sample.get(field, "") for field in fields])
        strengths = [s["forca"] for s in samples]
        append_values(
            summary,
            [
                room,
                names[room],
                min(strengths),
                max(strengths),
                round(sum(strengths) / len(strengths), 2),
                len(strengths),
            ],
        )
        format_sheet(sheet)
    format_sheet(summary)
    target = Path(caminho)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".xlsx", delete=False) as handle:
            temporary = Path(handle.name)
        workbook.save(temporary)
        os.replace(temporary, target)
    finally:
        workbook.close()
        if temporary:
            temporary.unlink(missing_ok=True)
    return str(target)
