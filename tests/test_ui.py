import threading
import time
import tkinter as tk

import pytest

from app_main import AppWiFiComodos
from wifi_coleta import WiFiReading


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def app(monkeypatch, tk_root):
    root = tk.Toplevel(tk_root)
    root.withdraw()
    app = AppWiFiComodos(root, reader=lambda **kwargs: WiFiReading(60, "Wi-Fi", "Demo"))
    monkeypatch.setattr("app_main.messagebox.askyesno", lambda *a, **k: True)
    monkeypatch.setattr("app_main.messagebox.askyesnocancel", lambda *a, **k: False)
    yield app
    if not app._closing:
        app._stop.set()
        if app._worker:
            app._worker.join(2)
        app.dirty = False
        app.fechar()


def pump_until(app, condition, timeout=3):
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.01)
    assert condition()


def test_collection_updates_tk_only_on_main_thread(app):
    main_thread = threading.get_ident()
    original = app.atualizar_texto
    calls = []

    def record(text):
        calls.append(threading.get_ident())
        original(text)

    app.atualizar_texto = record
    app.duracao_var.set("1")
    app.intervalo_var.set("1")
    app.iniciar_coleta()
    assert str(app.btn_carregar["state"]) == "disabled"
    assert str(app.btn_salvar["state"]) == "disabled"
    pump_until(app, lambda: not app.coletando)
    assert calls and all(identity == main_thread for identity in calls)
    assert app.dados_por_comodo["Sala"][0]["forca"] == 60
    assert app.dirty
    assert str(app.btn_salvar["state"]) == "normal"


def test_cancel_preserves_previous_room(app, rooms):
    app.dados_por_comodo = rooms.copy()
    original = app.dados_por_comodo["Sala"]
    app.iniciar_coleta()
    app.cancelar_coleta()
    pump_until(app, lambda: not app.coletando)
    assert app.dados_por_comodo["Sala"] is original
    assert not app.dirty
    assert str(app.btn_iniciar["state"]) == "normal"


def test_unexpected_failure_restores_controls(app, rooms):
    app.dados_por_comodo = rooms.copy()

    def broken(**kwargs):
        raise RuntimeError("simulated worker error")

    app.reader = broken
    app.iniciar_coleta()
    pump_until(app, lambda: not app.coletando)
    assert app.dados_por_comodo == rooms
    assert str(app.btn_iniciar["state"]) == "normal"


def test_close_during_collection_stops_worker_without_tk_access(app):
    app.iniciar_coleta()
    worker = app._worker
    app.fechar()
    worker.join(2)
    assert app._closing and not worker.is_alive()
