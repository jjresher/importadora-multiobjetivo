"""Etapa 3: frente de Pareto costo–tiempo por ε-restricción.

1. Extremos: min C (desempatando por T) y min T (desempatando por C).
2. ε-restricción: N_TAU límites τ uniformes entre T_min y T(min C); min C s.t. T <= τ,
   y luego min T s.t. C <= C* (lexicográfico, para no quedar con T holgado).
   Refinamiento: como los flujos son continuos, dentro de cada configuración de bodegas
   el frente es un tramo continuo; donde dos puntos eficientes consecutivos quedan a más
   de GAP_T días y GAP_C COP, se prueba el τ intermedio (hasta MAX_REFINAR resoluciones extra).
3. Se eliminan puntos repetidos y dominados.
4. Gráfica costo (X, M COP) vs tiempo (Y, días) con las bodegas abiertas.
5. Por punto: bodegas, asignación por zona, utilización y flujos por puerto.
6. Planes de la votación (Medellín B002, Cali B003, Barranquilla B004) y la mejor
   candidata de cada una de esas ciudades, ubicados respecto al frente.
7. Sensibilidad: rutas imputadas usadas y bodegas excluidas por datos faltantes.
8. Escenarios: cada configuración del frente evaluada en los 12 meses del pronóstico.

Uso:  python src/pareto.py   (requiere haber corrido src/limpieza.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modelo import (BODEGA_EXISTENTE, RAIZ, cargar_tablas, resolver,  # noqa: E402
                    validar_solucion)

SALIDA = RAIZ / "reports" / "pareto"
N_TAU = 10               # límites intermedios de τ (además de los dos extremos)
EPS_C = 1e-7             # holgura relativa del costo en el paso lexicográfico
EPS_T = 1e-6             # holgura absoluta del tiempo (días)
GAP_T = 0.0015           # hueco en T (días) que dispara un τ intermedio...
GAP_C = 1e6              # ...si además los extremos difieren en más de 1 M COP
MAX_REFINAR = 20         # resoluciones extra como máximo en el refinamiento

VOTACION = {"Medellín": "B002", "Cali": "B003", "Barranquilla": "B004"}

# Paleta de referencia (skill dataviz), modo claro
SUPERFICIE, TINTA, TINTA_2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
SERIE_1, SERIE_2 = "#2a78d6", "#eb6834"


def lexicografico(tablas, primero, tau=None, **kw):
    """Optimiza `primero` y luego el otro objetivo sin empeorar el primero."""
    if primero == "costo":
        s1 = resolver(tablas, objetivo="costo", tau=tau, **kw)
        if s1.estado != "Optimal":
            return s1
        return resolver(tablas, objetivo="tiempo", costo_max=s1.costo * (1 + EPS_C), tau=tau, **kw)
    s1 = resolver(tablas, objetivo="tiempo", **kw)
    return resolver(tablas, objetivo="costo", tau=s1.tiempo + EPS_T, **kw)


def no_dominados(puntos):
    """Filtra puntos repetidos (mismas bodegas y métricas) y dominados."""
    unicos = {}
    for p in puntos:
        clave = (tuple(p.abiertas), round(p.costo), round(p.tiempo, 5))
        unicos.setdefault(clave, p)
    lista = sorted(unicos.values(), key=lambda p: (p.costo, p.tiempo))
    eficientes = []
    for p in lista:
        dominado = any(q.costo <= p.costo + 1 and q.tiempo <= p.tiempo + 1e-9
                       and (q.costo < p.costo - 1 or q.tiempo < p.tiempo - 1e-9) for q in lista)
        if not dominado:
            eficientes.append(p)
    return eficientes


def dominado_por(c, t, frente):
    """Puntos del frente que dominan (c, t)."""
    return [q for q in frente if q.costo <= c and q.tiempo <= t and (q.costo < c or q.tiempo < t)]


def etiqueta(sol, bodegas):
    mun = bodegas.set_index("bodega_id")["municipio"]
    return " + ".join(f"{j} {mun[j]}" for j in sol.abiertas) or "solo B001"


def configuraciones(frente):
    """Agrupa los puntos eficientes por configuración de bodegas (en orden de costo)."""
    grupos = {}
    for k, p in enumerate(frente, 1):
        grupos.setdefault(tuple(p.abiertas), []).append((k, p))
    return grupos


def _dibujar(ax, frente, votacion, bodegas, zoom=False):
    xs = [p.costo / 1e6 for p in frente]
    ys = [p.tiempo for p in frente]
    ax.set_facecolor(SUPERFICIE)
    for conf, pts in configuraciones(frente).items():   # línea solo dentro de una configuración
        ax.plot([p.costo / 1e6 for _, p in pts], [p.tiempo for _, p in pts],
                color=SERIE_1, lw=2, zorder=2)
    ax.scatter(xs, ys, s=64, color=SERIE_1, edgecolor=SUPERFICIE, linewidth=2, zorder=3,
               label="Frente de Pareto (soluciones eficientes)")
    grupos = configuraciones(frente)
    for conf, pts in grupos.items():
        ks = [k for k, _ in pts]
        rango = f"P{ks[0]}" if len(ks) == 1 else f"P{ks[0]}–P{ks[-1]}"
        k0, p0 = pts[0]
        txt = f"{rango}: {etiqueta(p0, bodegas)}"
        if zoom:
            ax.annotate(txt, (p0.costo / 1e6, p0.tiempo), xytext=(10, 2),
                        textcoords="offset points", fontsize=7.5, color=TINTA)
    vx = [v["sol"].costo / 1e6 for v in votacion]
    vy = [v["sol"].tiempo for v in votacion]
    ax.scatter(vx, vy, s=80, marker="D", color=SERIE_2, edgecolor=SUPERFICIE, linewidth=2,
               zorder=3, label="Planes de la votación inicial")
    ax.grid(True, color=REJILLA, lw=1)
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_color(REJILLA)
    ax.tick_params(colors=TINTA_2, labelsize=8)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    return grupos


def graficar(frente, votacion, bodegas, ruta):
    fig, (ax, az) = plt.subplots(1, 2, figsize=(13, 6.2), dpi=150,
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    fig.patch.set_facecolor(SUPERFICIE)
    grupos = _dibujar(ax, frente, votacion, bodegas)
    # Vista general: una etiqueta por configuración (escalonadas hacia arriba) y por plan votado
    for n, (conf, pts) in enumerate(grupos.items()):
        ks = [k for k, _ in pts]
        rango = f"P{ks[0]}" if len(ks) == 1 else f"P{ks[0]}–P{ks[-1]}"
        _, p0 = pts[0]
        off = (10, -3) if n == 0 else (4, 16 + 17 * (n - 1))
        ax.annotate(f"{rango}: {etiqueta(p0, bodegas)}", (p0.costo / 1e6, p0.tiempo), xytext=off,
                    textcoords="offset points", fontsize=7.5, color=TINTA,
                    arrowprops=None if n == 0 else dict(arrowstyle="-", color=TINTA_2, lw=0.6))
    for v in votacion:
        izq = v["ciudad"] != "Medellín"
        ax.annotate(f"Votación: solo {v['ciudad']} ({v['bodega']})",
                    (v["sol"].costo / 1e6, v["sol"].tiempo), xytext=(-10 if izq else 10, 0),
                    textcoords="offset points", fontsize=7.5, color=TINTA_2,
                    ha="right" if izq else "left", va="center")
    ax.set_xlabel("Costo mensual total (millones COP)", color=TINTA)
    ax.set_ylabel("Tiempo promedio de entrega (días)", color=TINTA)
    ax.set_title("Vista general", color=TINTA, loc="left", fontsize=10)
    ax.legend(frameon=False, loc="upper left", fontsize=8, labelcolor=TINTA)
    # Zoom sobre el tramo denso del frente
    _dibujar(az, frente, votacion, bodegas, zoom=True)
    fx = [p.costo / 1e6 for p in frente]
    fy = [p.tiempo for p in frente]
    lo, hi = min(fy), sorted(fy)[-2] if len(fy) > 1 else max(fy)
    dx = max(fx) - min(fx)
    az.set_xlim(min(fx) - 0.03 * dx, max(fx) + 0.45 * dx)
    az.set_ylim(lo - 0.08 * (hi - lo), hi + 0.25 * (hi - lo))
    for k, p in enumerate(frente, 1):
        if lo - 1e-9 <= p.tiempo <= hi + 1e-9:
            az.annotate(f"P{k}", (p.costo / 1e6, p.tiempo), xytext=(-4, -12),
                        textcoords="offset points", fontsize=7, color=TINTA_2, ha="right")
    az.set_xlabel("Costo mensual total (millones COP)", color=TINTA)
    az.set_title(f"Detalle: T entre {lo:.3f} y {hi:.3f} días", color=TINTA, loc="left", fontsize=10)
    fig.suptitle("Frente de Pareto costo vs. tiempo de entrega — octubre de 2026 "
                 "(B001 Bogotá siempre abierta)", color=TINTA, x=0.01, ha="left", fontsize=11.5)
    fig.tight_layout()
    fig.savefig(ruta, facecolor=SUPERFICIE)
    plt.close(fig)


def guardar_detalle(frente, tablas):
    b = tablas.bodegas.set_index("bodega_id")
    dem = tablas.demanda.set_index("zona_id")
    filas, asig, util, flujos = [], [], [], []
    for k, p in enumerate(frente, 1):
        pid = f"P{k}"
        filas.append({"punto": pid, "bodegas_nuevas": " + ".join(p.abiertas),
                      "municipios": " + ".join(b.at[j, "municipio"] for j in p.abiertas),
                      "costo_mcop": p.costo / 1e6, "tiempo_dias": p.tiempo,
                      **{f"{c}_mcop": v / 1e6 for c, v in p.desglose.items()}})
        a = p.asignacion.assign(punto=pid)
        a["ciudad"] = a["zona_id"].map(dem["ciudad"])
        asig.append(a[["punto", "zona_id", "ciudad", "bodega_id", "pedidos",
                       "tiempo_entrega_dias", "costo_distribucion_cop_pedido"]])
        util.append(p.utilizacion.assign(punto=pid))
        flujos.append(p.abastecimiento.assign(punto=pid)[["punto", "puerto_id", "bodega_id", "pedidos"]])
    res = pd.DataFrame(filas)
    res.to_csv(SALIDA / "puntos_eficientes.csv", index=False)
    pd.concat(asig).to_csv(SALIDA / "asignacion_por_zona.csv", index=False)
    pd.concat(util)[["punto", "bodega_id", "municipio", "capacidad", "pedidos", "utilizacion"]] \
        .to_csv(SALIDA / "utilizacion_bodegas.csv", index=False)
    pd.concat(flujos).to_csv(SALIDA / "flujos_puertos.csv", index=False)
    # Tiempo promedio por zona y ciudad en cada punto (para "qué zonas mejoran")
    a = pd.concat(asig)
    a["t_x"] = a["pedidos"] * a["tiempo_entrega_dias"]
    por_zona = a.groupby(["punto", "zona_id", "ciudad"])[["t_x", "pedidos"]].sum()
    por_zona["tiempo_promedio"] = por_zona["t_x"] / por_zona["pedidos"]
    por_zona["tiempo_promedio"].unstack("punto").reset_index() \
        .to_csv(SALIDA / "tiempo_por_zona.csv", index=False, float_format="%.3f")
    por_ciudad = a.groupby(["punto", "ciudad"])[["t_x", "pedidos"]].sum()
    (por_ciudad["t_x"] / por_ciudad["pedidos"]).unstack("punto").reset_index() \
        .to_csv(SALIDA / "tiempo_por_ciudad.csv", index=False, float_format="%.3f")
    return res


def _tablas_con(cambio=None):
    """Tablas del modelo con un cambio opcional: función que recibe y modifica las tablas."""
    t = cargar_tablas()
    if cambio:
        cambio(t)
    return t


def sensibilidad_imputadas(frente):
    """Rutas imputadas con flujo en el frente; se varía su valor ±15 % y se re-resuelve."""
    cambios = pd.read_csv(RAIZ / "reports" / "cambios_limpieza.csv")
    imp = cambios[(cambios["accion"] == "imputado") & cambios["archivo"].str.startswith(("07", "08"))]
    filas = []
    for k, p in enumerate(frente, 1):
        usadas = set(p.asignacion["bodega_id"] + "|" + p.asignacion["zona_id"]) \
            | set(p.abastecimiento["puerto_id"] + "|" + p.abastecimiento["bodega_id"])
        for r in imp[imp["clave"].isin(usadas)].itertuples():
            filas.append({"punto": f"P{k}", "tiempo": p.tiempo, "costo": p.costo,
                          "archivo": r.archivo, "clave": r.clave, "campo": r.campo})
    usadas = pd.DataFrame(filas)
    if usadas.empty:
        return usadas
    salida = []
    for (arch, clave, campo), g in usadas.groupby(["archivo", "clave", "campo"]):
        cols = ["puerto_id", "bodega_id"] if arch.startswith("07") else ["bodega_id", "zona_id"]
        tabla = "arcos_in" if arch.startswith("07") else "arcos_out"
        a, b_ = clave.split("|")

        def cambio(t, f):
            df = getattr(t, tabla)
            df.loc[(df[cols[0]] == a) & (df[cols[1]] == b_), campo] *= f

        for f in (0.85, 1.15):
            t = _tablas_con(lambda t: cambio(t, f))
            mc = lexicografico(t, "costo")
            for r in g.itertuples():
                s = lexicografico(t, "costo", tau=r.tiempo + EPS_T)
                salida.append({"ruta": clave, "campo": campo, "factor": f, "punto": r.punto,
                               "config_punto": " + ".join(frente[int(r.punto[1:]) - 1].abiertas),
                               "config_nueva": " + ".join(s.abiertas),
                               "delta_costo_mcop": round((s.costo - r.costo) / 1e6, 2),
                               "min_costo_config": " + ".join(mc.abiertas),
                               "min_costo_T": round(mc.tiempo, 3)})
    return pd.DataFrame(salida)


def sensibilidad_excluidas(frente):
    """¿Entrarían al frente las bodegas excluidas por datos faltantes, con supuestos optimistas?

    No es una imputación: a cada sitio se le da el valor más favorable plausible (capacidad =
    máxima del dataset; costo fijo = 0) y se re-resuelve min C con T <= τ en un punto
    representativo de cada configuración del frente. Si ni así entra, la exclusión no afecta
    el resultado. Si entra con costo fijo 0, el ahorro obtenido es el costo fijo de
    equilibrio: el sitio solo convendría si su costo fijo real fuera menor que eso.
    """
    todas = pd.read_csv(RAIZ / "data" / "clean" / "bodegas.csv")
    rin = pd.read_csv(RAIZ / "data" / "clean" / "rutas_puerto_bodega.csv")
    rout = pd.read_csv(RAIZ / "data" / "clean" / "rutas_bodega_zona.csv")
    excl = todas[todas["habilitada_modelo"] == 0]
    cap_max = todas["capacidad_pedidos_mes"].max()
    fijo_min = todas.loc[(todas["habilitada_modelo"] == 1) & (todas["tipo"] == "candidata"),
                         "costo_fijo_adicional_cop_mes"].min()
    reps = [pts[0][1] for pts in configuraciones(frente).values()]
    filas = []
    for r in excl.itertuples():
        falta_cap = pd.isna(r.capacidad_pedidos_mes)
        cap = cap_max if falta_cap else r.capacidad_pedidos_mes
        fijo = r.costo_fijo_adicional_cop_mes if pd.notna(r.costo_fijo_adicional_cop_mes) else 0

        def agregar(t):
            nueva = pd.DataFrame([{"bodega_id": r.bodega_id, "municipio": r.municipio, "sitio": r.sitio,
                                   "tipo": r.tipo, "latitud": r.latitud, "longitud": r.longitud,
                                   "capacidad": cap, "costo_fijo": fijo,
                                   "costo_variable": r.costo_operacion_variable_cop_pedido}])
            t.bodegas = pd.concat([t.bodegas, nueva], ignore_index=True)
            t.arcos_in = pd.concat([t.arcos_in, rin[rin["arco_valido"] & (rin["bodega_id"] == r.bodega_id)]
                                    [t.arcos_in.columns]], ignore_index=True)
            t.arcos_out = pd.concat([t.arcos_out, rout[rout["arco_valido"] & (rout["bodega_id"] == r.bodega_id)]
                                     [t.arcos_out.columns]], ignore_index=True)

        t = _tablas_con(agregar)
        entra_en, ahorro = [], 0.0
        for base in reps:
            s = resolver(t, tau=base.tiempo + EPS_T)
            if r.bodega_id in s.abiertas and s.costo < base.costo - 1:
                entra_en.append(f"T<={base.tiempo:.3f}")
                ahorro = max(ahorro, (base.costo - s.costo) / 1e6)
        filas.append({
            "bodega_id": r.bodega_id, "municipio": r.municipio,
            "dato_faltante": "capacidad" if falta_cap else "costo fijo",
            "supuesto_optimista": f"capacidad={cap:,.0f} (máx. del dataset)" if falta_cap else "costo fijo=0",
            "entra_al_frente": bool(entra_en), "en": ", ".join(entra_en),
            "ahorro_max_mcop": round(ahorro, 1),
            "costo_fijo_equilibrio_mcop": round(ahorro, 1) if (entra_en and not falta_cap) else None,
            "costo_fijo_min_dataset_mcop": fijo_min / 1e6})
    return pd.DataFrame(filas)


def escenarios_mensuales(frente):
    """Evalúa cada configuración del frente y la de mínimo costo libre en los 12 meses del
    pronóstico limpio (misma red y costos; cambian demanda y oferta portuaria)."""
    import limpieza as L
    from modelo import Tablas
    C = RAIZ / "data" / "clean"
    leer = lambda n: pd.read_csv(C / f"{n}.csv")
    zonas, pron, bod = leer("zonas"), leer("pronostico_demanda"), leer("bodegas")
    of, ctrl = leer("oferta_puertos"), leer("controles_mensuales")
    rpb, rbz = leer("rutas_puerto_bodega"), leer("rutas_bodega_zona")
    confs = [set(c) for c in configuraciones(frente)]
    filas = []
    for mes in ctrl["mes"]:
        t = Tablas(*L.construir_modelo_mes(mes, zonas, pron, bod, of, ctrl, rpb, rbz))
        libre = resolver(t)
        fila = {"mes": mes, "demanda": int(t.demanda["demanda"].sum()),
                "min_costo_libre": " + ".join(libre.abiertas),
                "min_costo_libre_mcop": libre.costo / 1e6, "min_costo_libre_T": libre.tiempo}
        for c in confs:
            s = resolver(t, bodegas_fijas=c)
            nombre = " + ".join(sorted(c))
            fila[f"{nombre} | mcop"] = s.costo / 1e6 if s.estado == "Optimal" else None
            fila[f"{nombre} | T"] = s.tiempo if s.estado == "Optimal" else None
        filas.append(fila)
    return pd.DataFrame(filas)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    tablas = cargar_tablas()
    bodegas = tablas.bodegas

    # 1. Extremos
    min_c = lexicografico(tablas, "costo")
    min_t = lexicografico(tablas, "tiempo")
    print(f"Mínimo costo:  C={min_c.costo / 1e6:,.1f} M  T={min_c.tiempo:.4f}  {min_c.abiertas}")
    print(f"Mínimo tiempo: C={min_t.costo / 1e6:,.1f} M  T={min_t.tiempo:.4f}  {min_t.abiertas}")

    # 2. ε-restricción
    taus = np.linspace(min_t.tiempo, min_c.tiempo, N_TAU + 2)[1:-1]
    puntos = [min_c, min_t]
    for tau in taus:
        s = lexicografico(tablas, "costo", tau=float(tau))
        print(f"  τ={tau:.4f}: C={s.costo / 1e6:,.1f} M  T={s.tiempo:.4f}  {s.abiertas}")
        puntos.append(s)

    # Refinamiento adaptativo: entre dos puntos eficientes consecutivos a y b (T_a < T_b), los τ
    # ya probados en (T_a, T_b) devolvieron a; el tramo sin explorar es (máx τ probado, T_b).
    probados = [float(t) for t in taus]
    for _ in range(MAX_REFINAR):
        f = sorted(no_dominados(puntos), key=lambda p: p.tiempo)
        huecos = []
        for a, b in zip(f, f[1:]):
            lo = max([a.tiempo] + [t for t in probados if a.tiempo < t < b.tiempo])
            if b.tiempo - lo > GAP_T and a.costo - b.costo > GAP_C:
                huecos.append((b.tiempo - lo, (lo + b.tiempo) / 2))
        if not huecos:
            break
        tau = max(huecos)[1]
        probados.append(tau)
        s = lexicografico(tablas, "costo", tau=tau)
        print(f"  τ={tau:.4f} (refinado): C={s.costo / 1e6:,.1f} M  T={s.tiempo:.4f}  {s.abiertas}")
        puntos.append(s)

    # 3. Filtrar
    frente = no_dominados(puntos)
    for p in frente:
        validar_solucion(tablas, p)
    print(f"\n{len(puntos)} soluciones → {len(frente)} eficientes distintas")

    # 5. Detalle por punto
    res = guardar_detalle(frente, tablas)
    print(res[["punto", "bodegas_nuevas", "municipios", "costo_mcop", "tiempo_dias"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    # 6. Votación inicial y mejor candidata por ciudad votada
    votacion, filas = [], []
    for ciudad, j in VOTACION.items():
        s = resolver(tablas, bodegas_fijas={j})
        validar_solucion(tablas, s)
        votacion.append({"ciudad": ciudad, "bodega": j, "sol": s})
        dom = dominado_por(s.costo, s.tiempo, frente)
        mejor = min(dom, key=lambda q: q.costo) if dom else None
        # Mejor candidata única en la misma ciudad (min C con apertura restringida a esa ciudad)
        cands = bodegas[(bodegas["municipio"] == ciudad) & (bodegas["bodega_id"] != BODEGA_EXISTENTE)]
        alt = min((resolver(tablas, bodegas_fijas={c}) for c in cands["bodega_id"]),
                  key=lambda q: q.costo)
        filas.append({"plan": f"Votación: solo {ciudad}", "bodega": j,
                      "costo_mcop": s.costo / 1e6, "tiempo_dias": s.tiempo,
                      "eficiente": not dom,
                      "dominado_por": ", ".join(f"P{frente.index(q) + 1}" for q in dom),
                      "sobrecosto_vs_mejor_dominante_mcop": (s.costo - mejor.costo) / 1e6 if mejor else 0,
                      "mejor_candidata_en_ciudad": alt.abiertas[0],
                      "costo_mejor_candidata_mcop": alt.costo / 1e6,
                      "tiempo_mejor_candidata_dias": alt.tiempo})
    comp = pd.DataFrame(filas)
    comp.to_csv(SALIDA / "comparativo_votacion.csv", index=False)
    print("\nVotación inicial frente al modelo:")
    print(comp.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    # 4. Gráfica
    graficar(frente, votacion, bodegas, SALIDA / "frente_pareto.png")

    # 7. Sensibilidad
    imp = sensibilidad_imputadas(frente)
    imp.to_csv(SALIDA / "sensibilidad_rutas_imputadas.csv", index=False)
    print("\nRutas imputadas con flujo en el frente (±15 %):")
    print(imp.to_string(index=False) if len(imp) else "ninguna")
    excl = sensibilidad_excluidas(frente)
    excl.to_csv(SALIDA / "sensibilidad_bodegas_excluidas.csv", index=False)
    print("\nBodegas excluidas con supuestos optimistas:")
    print(excl.to_string(index=False))
    esc = escenarios_mensuales(frente)
    esc.to_csv(SALIDA / "escenarios_mensuales.csv", index=False, float_format="%.3f")
    print("\nConfiguraciones del frente en los 12 meses del pronóstico (costo M COP; vacío = infactible):")
    print(esc[["mes", "demanda", "min_costo_libre"] + [c for c in esc.columns if c.endswith("mcop")]]
          .to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    print(f"\nResultados en {SALIDA.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
