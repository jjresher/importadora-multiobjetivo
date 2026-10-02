"""Gráficas pensadas para proyectar: pocas etiquetas, letra grande.

Solo leen los CSV de reports/pareto/ (no resuelven nada), así que se pueden llamar desde el
notebook o desde la terminal en menos de un segundo.

Uso:  python src/graficas.py   → reports/pareto/frente_claro.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PARETO = RAIZ / "reports" / "pareto"

SUPERFICIE, TINTA, TINTA_2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
AZUL, NARANJA = "#2a78d6", "#eb6834"


def _es(valor, decimales=0):
    """Formato español: 1.575,2"""
    return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def frente_claro(ruta=None, mostrar=False):
    """Frente de Pareto: 9 planes eficientes y los 3 planes de la votación inicial."""
    f = pd.read_csv(PARETO / "puntos_eficientes.csv")
    v = pd.read_csv(PARETO / "comparativo_votacion.csv")
    fig, ax = plt.subplots(figsize=(12, 6.8), dpi=150)
    fig.patch.set_facecolor(SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)

    ax.scatter(f.costo_mcop, f.tiempo_dias, s=110, color=AZUL, edgecolor=SUPERFICIE,
               linewidth=2, zorder=3, label="Plan eficiente (9)")
    ax.scatter(v.costo_mcop, v.tiempo_dias, s=150, marker="D", color=NARANJA,
               edgecolor=SUPERFICIE, linewidth=2, zorder=3, label="Plan de la votación (3)")

    def rotulo(x, y, txt, dx, dy, ha="left", color=TINTA, **kw):
        ax.annotate(txt, (x, y), xytext=(dx, dy), textcoords="offset points",
                    fontsize=13, color=color, ha=ha, va="center", **kw)

    p = f.set_index("punto")
    rotulo(p.costo_mcop["P1"], p.tiempo_dias["P1"], "P1 · solo B012 Medellín\n"
           f"{_es(p.costo_mcop['P1'])} M · {_es(p.tiempo_dias['P1'], 2)} días", 4, 36)
    rotulo(p.costo_mcop["P2"], p.tiempo_dias["P2"], "P2 · B012 + B013\n(el codo)", 4, -34)
    rotulo(p.costo_mcop["P6"], p.tiempo_dias["P6"], "P5–P7 · B012 + B015", 0, -26, ha="center")
    rotulo(p.costo_mcop["P9"], p.tiempo_dias["P9"], "P8–P9 · B010 + B015", 0, -26, ha="center")
    nombres = {"B002": "solo Medellín", "B003": "solo Cali", "B004": "solo Barranquilla"}
    for r in v.itertuples():
        rotulo(r.costo_mcop, r.tiempo_dias, f"Votación: {nombres[r.bodega]}",
               -14 if r.bodega != "B002" else 14, 0,
               ha="right" if r.bodega != "B002" else "left", color=TINTA_2)

    # Costo de seguir bajando el tiempo después del codo
    x0, x1, y = p.costo_mcop["P2"], p.costo_mcop["P9"], 1.2
    ax.annotate("", xy=(x1, y), xytext=(x0, y), arrowprops=dict(arrowstyle="<->", color=TINTA_2, lw=1.5))
    ax.text((x0 + x1) / 2, y + 0.035, f"+{_es(x1 - x0)} M al mes para bajar solo "
            f"{_es(p.tiempo_dias['P2'] - p.tiempo_dias['P9'], 2)} días",
            ha="center", va="bottom", fontsize=13, color=TINTA)

    ax.set_xlabel("Costo mensual total (millones de COP)", fontsize=14, color=TINTA)
    ax.set_ylabel("Tiempo promedio de entrega (días)", fontsize=14, color=TINTA)
    ax.set_xlim(1560, 1750)
    ax.set_ylim(0.93, 1.9)
    ax.grid(True, color=REJILLA, lw=1)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color(REJILLA)
    ax.tick_params(colors=TINTA_2, labelsize=13)
    fmt = matplotlib.ticker.FuncFormatter
    ax.xaxis.set_major_formatter(fmt(lambda x, _: _es(x)))
    ax.yaxis.set_major_formatter(fmt(lambda y, _: _es(y, 1)))
    ax.legend(frameon=False, loc="upper left", fontsize=13, labelcolor=TINTA)
    ax.set_title("Más abajo y a la izquierda es mejor", loc="left", fontsize=15, color=TINTA)
    fig.tight_layout()
    if ruta:
        fig.savefig(ruta, facecolor=SUPERFICIE)
    if mostrar:
        plt.show()
    else:
        plt.close(fig)
    return fig


if __name__ == "__main__":
    frente_claro(PARETO / "frente_claro.png")
    print(f"Guardado en {PARETO / 'frente_claro.png'}")
