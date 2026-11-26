"""BatSignal desktop application. All Tk calls run on the main thread."""

import logging
import threading
import time
import tkinter as tk
from functools import partial
from logging.handlers import RotatingFileHandler
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from app_paths import data_directory, resource_path
from wifi_coleta import collect_samples, get_wifi_reading
from wifi_dados import (
    carregar_mapeamento,
    deletar_mapeamento,
    listar_mapeamentos,
    salvar_mapeamento,
)
from wifi_exportacao import exportar_mapeamento_excel
from wifi_graficos import (
    comparar_mapeamentos,
    criar_grafico_barras,
    criar_grafico_comparacao,
    criar_grafico_linha,
)

logger = logging.getLogger(__name__)


class AppWiFiComodos:
    def __init__(self, root, reader=get_wifi_reading):
        self.root = root
        self.reader = reader
        self.dados_por_comodo = {}
        self.comodo_atual = None
        self.coletando = False
        self.dirty = False
        self._closing = False
        self._events = Queue()
        self._stop = threading.Event()
        self._worker = None
        self._last_network = None
        self.root.title("BatSignal — Mapeador de Wi-Fi")
        self.root.geometry("1050x800")
        self.root.minsize(900, 720)
        try:
            self.root.iconbitmap(str(resource_path("imagens/logo.ico")))
        except tk.TclError:
            logger.debug("Application icon is unavailable")
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.fechar)
        self._poll_id = self.root.after(100, self._process_events)

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)
        banner = tk.Frame(self.root, bg="#101A27")
        banner.grid(row=0, column=0, sticky="ew")
        self.logo_photo = None
        try:
            with Image.open(resource_path("imagens/logo.png")) as image:
                image.thumbnail((95, 95), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(image)
            tk.Label(banner, image=self.logo_photo, bg="#101A27").pack(side="left", padx=20, pady=8)
        except (OSError, tk.TclError):
            logger.warning("Could not load application logo")
        tk.Label(
            banner, text="BatSignal", font=("Segoe UI", 23, "bold"), bg="#101A27", fg="#55BFFF"
        ).pack(anchor="w", padx=12, pady=(15, 0))
        tk.Label(
            banner,
            text="Compare a cobertura Wi-Fi, cômodo por cômodo.",
            font=("Segoe UI", 11),
            bg="#101A27",
            fg="white",
        ).pack(anchor="w", padx=12, pady=(0, 15))

        settings = ttk.LabelFrame(self.root, text="Configuração da coleta", padding=12)
        settings.grid(row=1, column=0, sticky="ew", padx=16, pady=12)
        self.comodo_var = tk.StringVar(value="Sala")
        self.duracao_var = tk.StringVar(value="60")
        self.intervalo_var = tk.StringVar(value="5")
        self.interface_var = tk.StringVar()
        self._entries = []
        for column, (label, variable, width) in enumerate(
            [
                ("Cômodo", self.comodo_var, 23),
                ("Duração (s)", self.duracao_var, 12),
                ("Intervalo (s)", self.intervalo_var, 12),
                ("Interface (opcional)", self.interface_var, 22),
            ]
        ):
            ttk.Label(settings, text=label).grid(row=0, column=column, sticky="w", padx=6)
            entry = ttk.Entry(settings, textvariable=variable, width=width)
            entry.grid(row=1, column=column, sticky="ew", padx=6, pady=5)
            self._entries.append(entry)
            settings.columnconfigure(column, weight=1)
        self.entry_comodo = self._entries[0]
        ttk.Label(
            settings,
            text="Mantenha o computador parado durante a coleta. "
            "O percentual de sinal não mede a velocidade da internet.",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=6, pady=(6, 0))

        actions = ttk.Frame(self.root)
        actions.grid(row=2, column=0, sticky="ew", padx=16)
        self.btn_iniciar = ttk.Button(actions, text="Iniciar coleta", command=self.iniciar_coleta)
        self.btn_cancelar = ttk.Button(
            actions, text="Cancelar coleta", command=self.cancelar_coleta
        )
        self.btn_refazer = ttk.Button(actions, text="Refazer coleta", command=self.refazer_coleta)
        self.btn_proximo = ttk.Button(actions, text="Próximo cômodo", command=self.proximo_comodo)
        self.btn_graficos = ttk.Button(actions, text="Ver gráficos", command=self.mostrar_graficos)
        self.btn_comparar = ttk.Button(actions, text="Comparar antes/depois", command=self.comparar)
        for column, button in enumerate(
            [
                self.btn_iniciar,
                self.btn_cancelar,
                self.btn_refazer,
                self.btn_proximo,
                self.btn_graficos,
                self.btn_comparar,
            ]
        ):
            button.grid(row=0, column=column, padx=(0, 6), pady=4)
        self.progress = ttk.Progressbar(actions, maximum=100)
        self.progress.grid(row=1, column=0, columnspan=6, sticky="ew", pady=8)

        log_frame = ttk.LabelFrame(self.root, text="Leituras e status", padding=10)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=8)
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.network_var = tk.StringVar(value="Aguardando coleta")
        ttk.Label(log_frame, textvariable=self.network_var).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.text_output = tk.Text(
            log_frame, height=10, state="disabled", wrap="word", font=("Consolas", 10)
        )
        self.text_output.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.text_output.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.text_output.config(yscrollcommand=scrollbar.set)

        summary = ttk.LabelFrame(self.root, text="Cômodos mapeados", padding=10)
        summary.grid(row=4, column=0, sticky="ew", padx=16, pady=6)
        self.summary_list = tk.Listbox(summary, height=4, font=("Segoe UI", 10))
        self.summary_list.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(summary, command=self.summary_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.summary_list.config(yscrollcommand=scrollbar.set)

        storage = ttk.Frame(self.root, padding=(16, 6))
        storage.grid(row=5, column=0, sticky="ew")
        ttk.Label(storage, text="Mapeamento:").pack(side="left")
        self.nome_mapeamento_var = tk.StringVar(value="Mapeamento")
        name_entry = ttk.Entry(storage, textvariable=self.nome_mapeamento_var, width=24)
        name_entry.pack(side="left", padx=8)
        self._entries.append(name_entry)
        self.btn_salvar = ttk.Button(storage, text="Salvar JSON", command=self.salvar_dados)
        self.btn_carregar = ttk.Button(storage, text="Carregar JSON", command=self.carregar_dados)
        self.btn_exportar = ttk.Button(storage, text="Exportar Excel", command=self.exportar_excel)
        for button in (self.btn_salvar, self.btn_carregar, self.btn_exportar):
            button.pack(side="left", padx=4)
        ttk.Label(self.root, text=f"Dados locais: {data_directory()}", wraplength=990).grid(
            row=6, column=0, sticky="w", padx=16, pady=(4, 10)
        )
        self._set_controls()

    def _set_controls(self):
        idle = not self.coletando
        has_data = bool(self.dados_por_comodo)
        states = {
            self.btn_iniciar: idle,
            self.btn_cancelar: not idle,
            self.btn_refazer: idle and self.comodo_atual in self.dados_por_comodo,
            self.btn_proximo: idle and has_data,
            self.btn_graficos: idle and has_data,
            self.btn_salvar: idle and has_data,
            self.btn_exportar: idle and has_data,
            self.btn_carregar: idle,
            self.btn_comparar: idle,
        }
        for widget, enabled in states.items():
            widget.config(state="normal" if enabled else "disabled")
        for entry in self._entries:
            entry.config(state="normal" if idle else "disabled")

    def atualizar_texto(self, texto):
        self.text_output.config(state="normal")
        self.text_output.insert("end", texto + "\n")
        self.text_output.see("end")
        self.text_output.config(state="disabled")

    def limpar_texto(self):
        self.text_output.config(state="normal")
        self.text_output.delete("1.0", "end")
        self.text_output.config(state="disabled")

    def atualizar_resumo(self):
        self.summary_list.delete(0, "end")
        for room, samples in self.dados_por_comodo.items():
            values = [sample["forca"] for sample in samples]
            self.summary_list.insert(
                "end",
                f"{room}: média {sum(values) / len(values):.1f}%  |  "
                f"mín. {min(values):g}%  |  máx. {max(values):g}%  |  "
                f"{len(values)} medições",
            )

    def iniciar_coleta(self):
        if self.coletando:
            return
        room = self.comodo_var.get().strip()
        if not room:
            messagebox.showerror("Coleta", "Digite o nome do cômodo.", parent=self.root)
            return
        try:
            duration, interval = int(self.duracao_var.get()), int(self.intervalo_var.get())
            if duration <= 0 or interval <= 0 or interval > duration:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Coleta",
                "Use segundos inteiros positivos e intervalo menor ou igual à duração.",
                parent=self.root,
            )
            return
        if room in self.dados_por_comodo and not messagebox.askyesno(
            "Refazer coleta",
            f"Substituir as medições de '{room}' ao concluir?\n"
            "Se cancelar, as medições anteriores serão mantidas.",
            parent=self.root,
        ):
            return
        self.coletando = True
        self._active_room = room
        self._duration = duration
        self._started = time.monotonic()
        self._last_network = None
        self._stop = threading.Event()
        self._set_controls()
        self.limpar_texto()
        self.atualizar_texto(f"Coletando {room} — {duration}s, intervalo de {interval}s.")
        self.network_var.set("Consultando a conexão Wi-Fi…")
        self.progress["value"] = 0
        reader = partial(self.reader, interface=self.interface_var.get().strip() or None)
        self._worker = threading.Thread(
            target=collect_samples,
            args=(duration, interval, self._stop, self._events, reader),
            daemon=True,
        )
        self._worker.start()

    def cancelar_coleta(self):
        if self.coletando:
            self._stop.set()
            self.btn_cancelar.config(state="disabled")
            self.atualizar_texto("Cancelando… aguardando a consulta atual (até 5 segundos).")

    def _process_events(self):
        if self._closing:
            return
        # Bound work per tick so large queues cannot monopolize the event loop.
        for _ in range(100):
            try:
                kind, payload = self._events.get_nowait()
            except Empty:
                break
            if kind == "sample":
                network = (payload["interface"], payload["ssid"], payload["bssid"])
                if self._last_network and network != self._last_network:
                    self.atualizar_texto(
                        "Aviso: a interface, rede ou ponto de acesso mudou durante a coleta."
                    )
                self._last_network = network
                self.network_var.set(
                    f"Interface: {network[0] or '—'}  |  "
                    f"Rede: {network[1] or '—'}  |  AP: {network[2] or '—'}"
                )
                self.atualizar_texto(f"[{payload['tempo']}] Sinal: {payload['forca']}%")
            elif kind == "error":
                self.atualizar_texto("Aviso: " + payload)
            elif kind == "done":
                self._finish_collection(payload)
        if self.coletando:
            self.progress["value"] = min(
                99, (time.monotonic() - self._started) / self._duration * 100
            )
        self._poll_id = self.root.after(100, self._process_events)

    def _finish_collection(self, result):
        self.coletando = False
        if result["cancelled"] or self._stop.is_set():
            self.atualizar_texto("Coleta cancelada. As medições anteriores foram preservadas.")
            self.progress["value"] = 0
        elif result["error"]:
            self.atualizar_texto(result["error"])
            self.progress["value"] = 0
        elif result["samples"]:
            self.dados_por_comodo[self._active_room] = result["samples"]
            self.comodo_atual = self._active_room
            self.dirty = True
            self.atualizar_resumo()
            self.atualizar_texto(
                f"Coleta concluída: {len(result['samples'])} medições válidas. "
                "Salve o mapeamento para manter os resultados."
            )
            self.progress["value"] = 100
        else:
            self.atualizar_texto("Nenhuma medição válida. Os dados anteriores foram preservados.")
            self.progress["value"] = 0
        self._set_controls()

    def refazer_coleta(self):
        if self.comodo_atual and not self.coletando:
            self.comodo_var.set(self.comodo_atual)
            self.iniciar_coleta()

    def proximo_comodo(self):
        self.comodo_var.set("")
        self.entry_comodo.focus_set()
        self.progress["value"] = 0

    def mostrar_graficos(self):
        if self.coletando or not self.dados_por_comodo:
            return
        window = tk.Toplevel(self.root)
        window.title("BatSignal — Gráficos")
        window.geometry("1150x750")
        notebook = ttk.Notebook(window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        for title, build in (("Leituras", criar_grafico_linha), ("Médias", criar_grafico_barras)):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)
            build(self.dados_por_comodo, frame)

    def _show_error(self, title, error):
        logger.exception("%s failed", title)
        messagebox.showerror(title, str(error), parent=self.root)

    def salvar_dados(self):
        if self.coletando or not self.dados_por_comodo:
            return False
        try:
            path = salvar_mapeamento(self.nome_mapeamento_var.get().strip(), self.dados_por_comodo)
        except (OSError, ValueError) as exc:
            self._show_error("Salvar", exc)
            return False
        self.dirty = False
        self.atualizar_texto(f"Mapeamento salvo: {path}")
        return True

    def _confirm_unsaved(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel(
            "Dados não salvos", "Salvar o mapeamento atual antes de continuar?", parent=self.root
        )
        if answer is None:
            return False
        return self.salvar_dados() if answer else True

    def carregar_dados(self):
        if self.coletando:
            return
        try:
            surveys = listar_mapeamentos()
        except OSError as exc:
            self._show_error("Carregar", exc)
            return
        window = tk.Toplevel(self.root)
        window.title("Carregar mapeamento")
        window.geometry("750x400")
        window.transient(self.root)
        window.grab_set()
        ttk.Label(window, text="Escolha um mapeamento ou importe um arquivo JSON.").pack(pady=10)
        listing = tk.Listbox(window)
        listing.pack(fill="both", expand=True, padx=12)
        for survey in surveys:
            listing.insert(
                "end", f"{survey['nome']} — {survey['data']} ({survey['comodos']} cômodos)"
            )
        ttk.Label(
            window, text="Arquivos inválidos são ignorados na lista e registrados no log."
        ).pack(pady=5)

        def load(path=None):
            if path is None:
                selected = listing.curselection()
                if not selected:
                    return
                path = surveys[selected[0]]["caminho"]
            try:
                data = carregar_mapeamento(path)
            except (OSError, ValueError) as exc:
                self._show_error("Carregar", exc)
                return
            window.grab_release()
            if not self._confirm_unsaved():
                window.grab_set()
                return
            self.dados_por_comodo = data["comodos"]
            self.nome_mapeamento_var.set(data["nome"])
            self.comodo_atual = None
            self.dirty = False
            self.atualizar_resumo()
            self._set_controls()
            self.limpar_texto()
            self.atualizar_texto(f"Mapeamento carregado: {data['nome']}")
            window.destroy()

        def import_file():
            path = filedialog.askopenfilename(parent=window, filetypes=[("JSON", "*.json")])
            if path:
                load(path)

        def delete():
            selected = listing.curselection()
            if not selected:
                return
            index = selected[0]
            if not messagebox.askyesno(
                "Excluir", "Excluir permanentemente este JSON?", parent=window
            ):
                return
            try:
                deletar_mapeamento(surveys[index]["caminho"])
            except (OSError, ValueError) as exc:
                self._show_error("Excluir", exc)
                return
            surveys.pop(index)
            listing.delete(index)

        actions = ttk.Frame(window, padding=10)
        actions.pack()
        for text, command in (
            ("Carregar", load),
            ("Importar JSON", import_file),
            ("Excluir", delete),
            ("Fechar", window.destroy),
        ):
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=4)

    def exportar_excel(self):
        if self.coletando or not self.dados_por_comodo:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")]
        )
        if not path:
            return
        try:
            exportar_mapeamento_excel(path, self.dados_por_comodo)
        except (OSError, ValueError) as exc:
            self._show_error("Exportar", exc)
            return
        self.atualizar_texto(f"Excel exportado: {path}")

    def comparar(self):
        if self.coletando:
            return
        paths = []
        for title in ("Selecione o mapeamento ANTES", "Selecione o mapeamento DEPOIS"):
            path = filedialog.askopenfilename(
                parent=self.root,
                title=title,
                initialdir=data_directory(),
                filetypes=[("JSON", "*.json")],
            )
            if not path:
                return
            paths.append(path)
        try:
            before, after = [carregar_mapeamento(path) for path in paths]
            rows = comparar_mapeamentos(before["comodos"], after["comodos"])
        except (OSError, ValueError) as exc:
            self._show_error("Comparar", exc)
            return
        window = tk.Toplevel(self.root)
        window.title(f"Antes: {before['nome']} | Depois: {after['nome']}")
        window.geometry("1100x750")
        ttk.Label(
            window,
            text=f"{len(rows)} cômodos em comum. Diferenças em pontos percentuais; "
            "use o mesmo dispositivo e condições de coleta.",
        ).pack(pady=8)
        frame = ttk.Frame(window)
        frame.pack(fill="both", expand=True)
        criar_grafico_comparacao(before["comodos"], after["comodos"], frame)

    def fechar(self):
        if self.coletando and not messagebox.askyesno(
            "Sair", "Cancelar a coleta em andamento e fechar?", parent=self.root
        ):
            return
        if self.coletando and self.dirty:
            # Saving is disabled during collection. Let the user cancel, then save.
            messagebox.showinfo(
                "Dados não salvos",
                "Cancele a coleta e salve o mapeamento antes de fechar.",
                parent=self.root,
            )
            return
        if not self._confirm_unsaved():
            return
        self._closing = True
        self._stop.set()
        self.root.after_cancel(self._poll_id)
        self.root.destroy()


def configure_logging():
    directory = data_directory()
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / "batsignal.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    configure_logging()
    root = tk.Tk()
    AppWiFiComodos(root)
    root.mainloop()
