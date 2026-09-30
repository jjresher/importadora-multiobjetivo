"""Etapa 2: MILP de localización de bodegas y asignación de pedidos (sección 5 de CONTEXTO.md).

Variables:
  y_j  binaria   opera la bodega j (y_B001 = 1; como máximo `max_nuevas` aperturas nuevas)
  x_ji continua  pedidos de la bodega j a la zona i (solo arcos válidos)
  g_pj continua  pedidos del puerto p a la bodega j (solo arcos válidos)

Objetivos:
  C = Σ F_j y_j + Σ v_j Σ_i x_ji + Σ a_pj g_pj + Σ c_ji x_ji        (COP/mes)
  T = Σ t_ji x_ji / D                                                (días promedio)

Uso:
  from modelo import cargar_tablas, resolver
  tablas = cargar_tablas()                       # data/clean/modelo_202610_*.csv
  sol = resolver(tablas)                         # min C
  sol = resolver(tablas, objetivo="tiempo")      # min T
  sol = resolver(tablas, tau=2.0)                # min C s.t. T <= 2.0
  sol = resolver(tablas, bodegas_fijas={"B002"}) # evalúa un plan dado (B001 + B002)

  python src/modelo.py   → resuelve min C y valida la solución.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pulp

RAIZ = Path(__file__).resolve().parents[1]
CLEAN = RAIZ / "data" / "clean"

MES_BASE = "2026-10"
BODEGA_EXISTENTE = "B001"
MAX_NUEVAS = 2
TOL = 1e-6


@dataclass
class Tablas:
    demanda: pd.DataFrame     # zona_id, ciudad, demanda
    bodegas: pd.DataFrame     # bodega_id, municipio, ..., capacidad, costo_fijo, costo_variable
    oferta: pd.DataFrame      # puerto_id, oferta
    arcos_in: pd.DataFrame    # puerto_id, bodega_id, costo_abastecimiento_cop_pedido, ...
    arcos_out: pd.DataFrame   # bodega_id, zona_id, tiempo_entrega_dias, costo_distribucion_cop_pedido, ...


@dataclass
class Solucion:
    estado: str
    costo: float                      # C, COP/mes
    tiempo: float                     # T, días promedio
    abiertas: list[str]               # bodegas nuevas abiertas (sin B001)
    asignacion: pd.DataFrame          # bodega_id, zona_id, pedidos, tiempo, costo_distribucion
    abastecimiento: pd.DataFrame      # puerto_id, bodega_id, pedidos
    utilizacion: pd.DataFrame         # bodega_id, capacidad, pedidos, utilizacion
    desglose: dict = field(default_factory=dict)  # componentes de C
    segundos: float = 0.0


def cargar_tablas(mes: str = MES_BASE) -> Tablas:
    s = mes.replace("-", "")
    leer = lambda n: pd.read_csv(CLEAN / f"modelo_{s}_{n}.csv")
    return Tablas(leer("demanda"), leer("bodegas"), leer("oferta"),
                  leer("arcos_puerto_bodega"), leer("arcos_bodega_zona"))


def resolver(tablas: Tablas, objetivo: str = "costo", tau: float | None = None,
             costo_max: float | None = None, bodegas_fijas: set[str] | None = None,
             max_nuevas: int = MAX_NUEVAS, mip_gap: float = 0.0,
             tiempo_limite: int | None = None, verbose: bool = False) -> Solucion:
    """Construye y resuelve el MILP.

    objetivo       "costo" (min C) o "tiempo" (min T).
    tau            si se da, agrega T <= tau (ε-restricción sobre el tiempo).
    costo_max      si se da, agrega C <= costo_max (para desempatar min T por costo).
    bodegas_fijas  si se da, fija exactamente qué candidatas abren (evaluar un plan dado).
    """
    if objetivo not in ("costo", "tiempo"):
        raise ValueError("objetivo debe ser 'costo' o 'tiempo'")
    d = tablas.demanda.set_index("zona_id")["demanda"]
    s = tablas.oferta.set_index("puerto_id")["oferta"]
    b = tablas.bodegas.set_index("bodega_id")
    D = float(d.sum())
    if abs(s.sum() - D) > TOL:
        raise ValueError(f"Oferta total {s.sum():,.0f} != demanda total {D:,.0f}")

    a_in = tablas.arcos_in.set_index(["puerto_id", "bodega_id"])
    a_out = tablas.arcos_out.set_index(["bodega_id", "zona_id"])
    a_in = a_in[a_in.index.get_level_values("bodega_id").isin(b.index)]
    a_out = a_out[a_out.index.get_level_values("bodega_id").isin(b.index)
                  & a_out.index.get_level_values("zona_id").isin(d.index)]
    J, I, P = list(b.index), list(d.index), list(s.index)
    # Parámetros como floats de Python: PuLP 4 no compara bien expresiones con escalares numpy.
    dem = {k: float(v) for k, v in d.items()}
    ofe = {k: float(v) for k, v in s.items()}
    K = {k: float(v) for k, v in b["capacidad"].items()}
    F = {k: float(v) for k, v in b["costo_fijo"].items()}
    v_ = {k: float(v) for k, v in b["costo_variable"].items()}
    a = {k: float(v) for k, v in a_in["costo_abastecimiento_cop_pedido"].items()}
    c = {k: float(v) for k, v in a_out["costo_distribucion_cop_pedido"].items()}
    t = {k: float(v) for k, v in a_out["tiempo_entrega_dias"].items()}
    nuevas = [j for j in J if j != BODEGA_EXISTENTE]

    m = pulp.LpProblem("importadora", pulp.LpMinimize)
    y = {j: m.add_variable(f"y_{j}", cat="Binary") for j in J}
    x = {k: m.add_variable(f"x_{k[0]}_{k[1]}", lowBound=0) for k in a_out.index}
    g = {k: m.add_variable(f"g_{k[0]}_{k[1]}", lowBound=0) for k in a_in.index}

    sale = {j: [] for j in J}
    llega = {i: [] for i in I}
    for (j, i) in x:
        sale[j].append(x[j, i])
        llega[i].append(x[j, i])
    entra = {j: [] for j in J}
    for (p, j) in g:
        entra[j].append(g[p, j])

    c_fijo = pulp.lpSum(F[j] * y[j] for j in nuevas)
    c_var = pulp.lpSum(v_[j] * x[j, i] for (j, i) in x)
    c_abast = pulp.lpSum(a[k] * g[k] for k in g)
    c_dist = pulp.lpSum(c[k] * x[k] for k in x)
    C = c_fijo + c_var + c_abast + c_dist
    T = pulp.lpSum(t[k] * x[k] for k in x) * (1.0 / D)

    m += C if objetivo == "costo" else T

    for i in I:                                     # atender cada zona
        m += pulp.lpSum(llega[i]) == dem[i], f"dem_{i}"
    for j in J:                                     # capacidad y apertura; flujo entra = sale
        m += pulp.lpSum(sale[j]) <= K[j] * y[j], f"cap_{j}"
        m += pulp.lpSum(entra[j]) == pulp.lpSum(sale[j]), f"flujo_{j}"
    for p in P:                                     # oferta portuaria
        m += pulp.lpSum(g[k] for k in g if k[0] == p) == ofe[p], f"ofe_{p}"
    m += y[BODEGA_EXISTENTE] == 1, "existente"
    m += pulp.lpSum(y[j] for j in nuevas) <= max_nuevas, "max_nuevas"
    if bodegas_fijas is not None:
        desconocidas = set(bodegas_fijas) - set(nuevas)
        if desconocidas:
            raise ValueError(f"Bodegas no disponibles en el modelo: {desconocidas}")
        for j in nuevas:
            m += y[j] == (1 if j in bodegas_fijas else 0), f"fija_{j}"
    if tau is not None:
        m += T <= float(tau), "tau"
    if costo_max is not None:
        m += C <= float(costo_max), "costo_max"

    solver = pulp.HiGHS(msg=verbose, gapRel=mip_gap, timeLimit=tiempo_limite)
    stats = m.solve(solver)
    estado = stats.status.name
    if estado != "Optimal":
        return Solucion(estado, float("nan"), float("nan"), [], pd.DataFrame(),
                        pd.DataFrame(), pd.DataFrame(), segundos=stats.time)

    asig = pd.DataFrame([(j, i, x[j, i].value()) for (j, i) in x],
                        columns=["bodega_id", "zona_id", "pedidos"])
    asig = asig[asig["pedidos"] > TOL].merge(
        a_out[["tiempo_entrega_dias", "costo_distribucion_cop_pedido"]].reset_index(),
        on=["bodega_id", "zona_id"])
    abast = pd.DataFrame([(p, j, g[p, j].value()) for (p, j) in g],
                         columns=["puerto_id", "bodega_id", "pedidos"])
    abast = abast[abast["pedidos"] > TOL].reset_index(drop=True)
    abiertas = sorted(j for j in nuevas if y[j].value() > 0.5)
    operan = [BODEGA_EXISTENTE] + abiertas
    util = b.loc[operan, ["municipio", "capacidad"]].reset_index()
    util["pedidos"] = util["bodega_id"].map(asig.groupby("bodega_id")["pedidos"].sum()).fillna(0)
    util["utilizacion"] = util["pedidos"] / util["capacidad"]
    desglose = {"fijo": pulp.value(c_fijo), "variable": pulp.value(c_var),
                "abastecimiento": pulp.value(c_abast), "distribucion": pulp.value(c_dist)}
    return Solucion(estado, pulp.value(C), pulp.value(T), abiertas, asig.reset_index(drop=True),
                    abast, util, desglose, stats.time)


def validar_solucion(tablas: Tablas, sol: Solucion) -> list[str]:
    """Recalcula C y T con pandas (independiente de PuLP) y verifica todas las restricciones."""
    d = tablas.demanda.set_index("zona_id")["demanda"]
    s = tablas.oferta.set_index("puerto_id")["oferta"]
    b = tablas.bodegas.set_index("bodega_id")
    a_in = tablas.arcos_in.set_index(["puerto_id", "bodega_id"])
    x, g = sol.asignacion, sol.abastecimiento
    operan = set([BODEGA_EXISTENTE] + sol.abiertas)
    tol = 1e-4
    D = d.sum()

    atendido = x.groupby("zona_id")["pedidos"].sum().reindex(d.index, fill_value=0)
    assert (atendido - d).abs().max() < tol * D, "Demanda no atendida"
    salida = x.groupby("bodega_id")["pedidos"].sum()
    assert set(salida.index) <= operan, "Despacho desde bodega cerrada"
    assert (salida <= b.loc[salida.index, "capacidad"] + tol).all(), "Capacidad excedida"
    entrada = g.groupby("bodega_id")["pedidos"].sum().reindex(salida.index, fill_value=0)
    assert (entrada - salida).abs().max() < tol * D, "Flujo entra != sale"
    por_puerto = g.groupby("puerto_id")["pedidos"].sum().reindex(s.index, fill_value=0)
    assert (por_puerto - s).abs().max() < tol * D, "Oferta portuaria no usada exactamente"
    assert len(sol.abiertas) <= MAX_NUEVAS

    C = (b.loc[sol.abiertas, "costo_fijo"].sum()
         + (salida * b.loc[salida.index, "costo_variable"]).sum()
         + (g.set_index(["puerto_id", "bodega_id"])["pedidos"]
            * a_in.loc[list(zip(g["puerto_id"], g["bodega_id"])), "costo_abastecimiento_cop_pedido"].values).sum()
         + (x["pedidos"] * x["costo_distribucion_cop_pedido"]).sum())
    T = (x["pedidos"] * x["tiempo_entrega_dias"]).sum() / D
    assert abs(C - sol.costo) / C < 1e-6, f"C recalculado {C:,.0f} != {sol.costo:,.0f}"
    assert abs(T - sol.tiempo) < 1e-6, f"T recalculado {T} != {sol.tiempo}"
    return [f"Demanda atendida: {atendido.sum():,.0f} / {D:,.0f} en {len(d)} zonas",
            f"Oferta usada: " + ", ".join(f"{p}={v:,.0f}" for p, v in por_puerto.items()),
            f"C recalculado = {C:,.0f} COP (coincide) · T recalculado = {T:.4f} días (coincide)"]


def resumen(sol: Solucion, titulo: str = "") -> str:
    ln = [f"== {titulo} ==" if titulo else "",
          f"Estado: {sol.estado} ({sol.segundos:.1f} s)",
          f"Costo C: {sol.costo / 1e6:,.1f} M COP/mes · Tiempo T: {sol.tiempo:.3f} días",
          "Bodegas nuevas: " + (", ".join(sol.abiertas) or "ninguna"),
          "Desglose C (M COP): " + ", ".join(f"{k} {v / 1e6:,.1f}" for k, v in sol.desglose.items()),
          "Utilización:", sol.utilizacion.to_string(index=False, float_format=lambda v: f"{v:,.2f}"),
          "Abastecimiento:", sol.abastecimiento.to_string(index=False, float_format=lambda v: f"{v:,.0f}")]
    return "\n".join(ln)


def main():
    tablas = cargar_tablas()
    sol = resolver(tablas, objetivo="costo")
    print(resumen(sol, "Mínimo costo (mes base)"))
    for linea in validar_solucion(tablas, sol):
        print("✔", linea)

    # Sensibilidad: ¿la solución usa rutas imputadas en la limpieza? Si sí, variar su costo/tiempo ±15 %.
    cambios = pd.read_csv(RAIZ / "reports" / "cambios_limpieza.csv")
    imp = cambios[(cambios["accion"] == "imputado") & cambios["archivo"].str.startswith(("07", "08"))]
    usadas_out = set(sol.asignacion["bodega_id"] + "|" + sol.asignacion["zona_id"])
    usadas_in = set(sol.abastecimiento["puerto_id"] + "|" + sol.abastecimiento["bodega_id"])
    usadas = imp[imp["clave"].isin(usadas_out | usadas_in)]
    print("\nRutas imputadas con flujo en la solución:",
          ", ".join(f"{r.clave} ({r.campo})" for r in usadas.itertuples()) or "ninguna")
    for r in usadas.itertuples():
        for f in (0.85, 1.15):
            t = cargar_tablas()
            if r.archivo.startswith("07"):
                p, j = r.clave.split("|")
                mask = (t.arcos_in["puerto_id"] == p) & (t.arcos_in["bodega_id"] == j)
                t.arcos_in.loc[mask, r.campo] *= f
            else:
                j, i = r.clave.split("|")
                mask = (t.arcos_out["bodega_id"] == j) & (t.arcos_out["zona_id"] == i)
                t.arcos_out.loc[mask, r.campo] *= f
            s2 = resolver(t)
            print(f"  {r.clave} {r.campo} ×{f}: bodegas {s2.abiertas}, "
                  f"C {s2.costo / 1e6:,.1f} M, ΔC {(s2.costo - sol.costo) / 1e6:+.2f} M")


if __name__ == "__main__":
    main()
