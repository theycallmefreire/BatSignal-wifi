"""Chart builders usable both in Tkinter and in headless regression tests."""

from itertools import cycle

from matplotlib.figure import Figure
from matplotlib.patches import Patch

from wifi_dados import validar_comodos

COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")
MARKERS = ("o", "s", "^", "D", "v", "P", "X")


def _finish(figure, parent_frame):
    figure.tight_layout()
    if parent_frame is None:
        return figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    canvas = FigureCanvasTkAgg(figure, master=parent_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    return canvas


def criar_grafico_linha(dados_por_comodo, parent_frame=None):
    validar_comodos(dados_por_comodo)
    fig = Figure(figsize=(11, 6), dpi=100)
    ax = fig.add_subplot(111)
    for (room, samples), color, marker in zip(
        dados_por_comodo.items(), cycle(COLORS), cycle(MARKERS)
    ):
        values = [sample["forca"] for sample in samples]
        average = sum(values) / len(values)
        ax.plot(
            range(1, len(values) + 1),
            values,
            color=color,
            marker=marker,
            linewidth=1.8,
            label=f"{room} — média {average:.1f}%",
        )
        ax.axhline(average, color=color, linestyle="--", alpha=0.4, linewidth=1)
    ax.set(
        title="Sinal Wi-Fi por cômodo",
        xlabel="Número da medição",
        ylabel="Sinal (%)",
        ylim=(0, 100),
    )
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=8)
    return _finish(fig, parent_frame)


def cor_sinal(value):
    return "#009E73" if value > 95 else "#E69F00" if value > 92 else "#D55E00"


def criar_grafico_barras(dados_por_comodo, parent_frame=None):
    validar_comodos(dados_por_comodo)
    rows = []
    for room, samples in dados_por_comodo.items():
        values = [sample["forca"] for sample in samples]
        rows.append((room, sum(values) / len(values), min(values), max(values)))
    rows.sort(key=lambda row: row[1], reverse=True)
    fig = Figure(figsize=(11, max(5, len(rows) * 0.4)), dpi=100)
    ax = fig.add_subplot(111)
    averages = [row[1] for row in rows]
    bars = ax.barh(
        [row[0] for row in rows], averages, color=[cor_sinal(value) for value in averages]
    )
    ax.invert_yaxis()
    for bar, (_, mean, low, high) in zip(bars, rows):
        label = f"{mean:.1f}%  (mín. {low:g} / máx. {high:g})"
        ax.text(
            1,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85},
        )
    ax.set(title="Comparação do sinal médio por cômodo", xlabel="Sinal (%)", xlim=(0, 100))
    ax.grid(axis="x", alpha=0.2)
    ax.legend(
        handles=[
            Patch(color="#009E73", label="> 95%"),
            Patch(color="#E69F00", label="> 92% e ≤ 95%"),
            Patch(color="#D55E00", label="≤ 92%"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=3,
    )
    return _finish(fig, parent_frame)


def comparar_mapeamentos(antes, depois):
    validar_comodos(antes)
    validar_comodos(depois)
    rows = []
    for room in antes:
        if room in depois:
            previous = sum(s["forca"] for s in antes[room]) / len(antes[room])
            current = sum(s["forca"] for s in depois[room]) / len(depois[room])
            rows.append(
                {
                    "comodo": room,
                    "antes": previous,
                    "depois": current,
                    "diferenca": current - previous,
                }
            )
    if not rows:
        raise ValueError("Os mapeamentos não possuem cômodos com o mesmo nome.")
    return rows


def criar_grafico_comparacao(antes, depois, parent_frame=None):
    rows = comparar_mapeamentos(antes, depois)
    fig = Figure(figsize=(11, max(5, len(rows) * 0.55)), dpi=100)
    ax = fig.add_subplot(111)
    positions = list(range(len(rows)))
    ax.barh(
        [p - 0.18 for p in positions],
        [r["antes"] for r in rows],
        height=0.35,
        label="Antes",
        color="#0072B2",
    )
    ax.barh(
        [p + 0.18 for p in positions],
        [r["depois"] for r in rows],
        height=0.35,
        label="Depois",
        color="#E69F00",
    )
    ax.set_yticks(positions, [f"{r['comodo']} ({r['diferenca']:+.1f} p.p.)" for r in rows])
    ax.invert_yaxis()
    ax.set(
        xlim=(0, 100),
        xlabel="Sinal médio (%)",
        title="Antes / depois — apenas cômodos com o mesmo nome",
    )
    ax.legend()
    ax.grid(axis="x", alpha=0.2)
    return _finish(fig, parent_frame)
