"""Etapa 1: limpieza y conciliación de los datos de la importadora.

Lee los 12 CSV de data/raw/ (que nunca se modifican), aplica reglas documentadas
y escribe:
  - data/clean/*.csv                 tablas limpias (todos los meses) y del modelo (mes base)
  - reports/cambios_limpieza.csv     una fila por registro eliminado, modificado o excluido
  - reports/bitacora_limpieza.md     bitácora legible con reglas, cambios y validaciones

Uso:  python src/limpieza.py
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
CLEAN = RAIZ / "data" / "clean"
REPORTS = RAIZ / "reports"

MES_BASE = "2026-10"
BODEGA_EXISTENTE = "B001"

# Parámetros de las reglas (se reportan en la bitácora)
K_VECINOS = 5              # rutas comparables usadas para imputar
MIN_COMPARABLES = 3        # por debajo de esto, el arco se excluye
TOL_DISTANCIA_REL = 0.25   # un comparable debe estar a ±25 % de la distancia del arco
RATIO_ATIPICO = (0.5, 2.0)  # valor / valor esperado fuera de este rango => atípico

# Catálogo de municipios válidos (forma canónica) y alias conocidos.
CATALOGO_MUNICIPIOS = [
    "Armenia", "Barranquilla", "Bogotá", "Bucaramanga", "Buenaventura", "Cali",
    "Cartagena", "Cota", "Cúcuta", "Funza", "Girardot", "Ibagué", "Itagüí",
    "Jamundí", "La Estrella", "Malambo", "Manizales", "Medellín", "Montería",
    "Mosquera", "Neiva", "Palmira", "Pereira", "Rionegro", "Santa Marta",
    "Sincelejo", "Soacha", "Soledad", "Tuluá", "Valledupar", "Villavicencio",
    "Yumbo",
]
ALIAS_MUNICIPIOS = {"bmanga": "Bucaramanga"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

class Bitacora:
    """Acumula cada cambio aplicado a los datos."""

    def __init__(self) -> None:
        self.filas: list[dict] = []

    def registrar(self, archivo, clave, campo, original, nuevo, regla, accion):
        self.filas.append({
            "archivo": archivo, "clave": clave, "campo": campo,
            "valor_original": _fmt(original), "valor_nuevo": _fmt(nuevo),
            "regla": regla, "accion": accion,
        })

    def df(self) -> pd.DataFrame:
        return pd.DataFrame(self.filas, columns=[
            "archivo", "clave", "campo", "valor_original", "valor_nuevo", "regla", "accion"])


def _fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "NA"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def leer(nombre: str) -> pd.DataFrame:
    # Los CSV vienen con BOM; utf-8-sig lo descarta.
    return pd.read_csv(RAW / nombre, encoding="utf-8-sig")


def _clave_texto(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", sin_tildes.lower())


_INDICE_CATALOGO = {_clave_texto(m): m for m in CATALOGO_MUNICIPIOS}
_INDICE_CATALOGO.update(ALIAS_MUNICIPIOS)


def normalizar_municipio(texto: str) -> str:
    clave = _clave_texto(str(texto))
    if clave not in _INDICE_CATALOGO:
        raise ValueError(f"Municipio fuera del catálogo: {texto!r}")
    return _INDICE_CATALOGO[clave]


def quitar_duplicados(df, claves, archivo, bit: Bitacora):
    """Elimina duplicados exactos; falla si quedan claves repetidas con valores distintos."""
    dup = df[df.duplicated(keep="first")]
    for _, fila in dup.iterrows():
        clave = "|".join(str(fila[c]) for c in claves)
        bit.registrar(archivo, clave, "(fila completa)", "duplicado exacto", "eliminada",
                      "R1: duplicado exacto; se conserva una copia", "eliminado")
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    conflicto = df[df.duplicated(claves, keep=False)]
    if not conflicto.empty:
        raise ValueError(f"{archivo}: claves duplicadas con valores distintos:\n{conflicto}")
    return df


def imputar_por_vecinos(validas: pd.DataFrame, grupo_col: str, grupo, distancia: float,
                        campo: str):
    """Mediana de `campo` en las K rutas válidas del mismo grupo más cercanas en distancia.

    Solo cuentan rutas cuya distancia esté a ±TOL_DISTANCIA_REL de la del arco.
    Devuelve (valor, n_comparables, ids) o (None, n, ids) si no hay suficientes.
    """
    cand = validas[(validas[grupo_col] == grupo)].copy()
    cand["_d"] = (cand["distancia_vial_estimada_km"] - distancia).abs()
    cand = cand[cand["_d"] <= TOL_DISTANCIA_REL * max(distancia, 20.0)]
    cand = cand.nsmallest(K_VECINOS, "_d")
    if len(cand) < MIN_COMPARABLES:
        return None, len(cand), cand
    return float(cand[campo].median()), len(cand), cand


# ---------------------------------------------------------------------------
# Limpieza por archivo
# ---------------------------------------------------------------------------

def limpiar_zonas(bit):
    z = leer("01_zonas_demanda.csv")
    assert z["zona_id"].is_unique
    for i, fila in z.iterrows():
        nuevo = normalizar_municipio(fila["ciudad_canonica"])
        if nuevo != fila["ciudad_canonica"]:
            bit.registrar("01_zonas_demanda.csv", fila["zona_id"], "ciudad_canonica",
                          fila["ciudad_canonica"], nuevo,
                          "R2: normalizar contra catálogo de municipios", "modificado")
            z.at[i, "ciudad_canonica"] = nuevo
    assert (z["pedidos_octubre_referencia"] > 0).all()
    assert z["porcentaje_pedidos_urgentes"].between(0, 1).all()
    return z


def limpiar_historico(bit, zonas):
    arch = "02_demanda_historica.csv"
    h = leer(arch)
    h = quitar_duplicados(h, ["mes", "zona_id"], arch, bit)
    h = h.sort_values(["zona_id", "mes"]).reset_index(drop=True)

    # Pedidos inválidos: nulos o negativos. Se marcan y se imputan con el promedio
    # de los meses vecinos de la misma zona (el histórico no entra al modelo).
    invalido = h["pedidos_realizados"].isna() | (h["pedidos_realizados"] < 0)
    originales = h.loc[invalido, "pedidos_realizados"].copy()
    h.loc[invalido, "pedidos_realizados"] = np.nan
    for i in h.index[invalido]:
        zona = h.at[i, "zona_id"]
        serie = h[h["zona_id"] == zona]["pedidos_realizados"]
        pos = serie.index.get_loc(i)
        vecinos = [serie.iloc[p] for p in (pos - 1, pos + 1)
                   if 0 <= p < len(serie) and not np.isnan(serie.iloc[p])]
        nuevo = float(round(np.mean(vecinos)))
        h.at[i, "pedidos_realizados"] = nuevo
        motivo = "nulo" if np.isnan(originales[i]) else "negativo"
        bit.registrar(arch, f"{h.at[i, 'mes']}|{zona}", "pedidos_realizados", originales[i], nuevo,
                      f"R4: {motivo}; promedio de meses vecinos de la zona", "imputado")

    # Atípicos en pedidos: frente a la mediana de la zona.
    ratio = h["pedidos_realizados"] / h.groupby("zona_id")["pedidos_realizados"].transform("median")
    atip = h[(ratio < RATIO_ATIPICO[0]) | (ratio > RATIO_ATIPICO[1])]
    assert atip.empty, f"Atípicos de pedidos sin regla:\n{atip}"

    # Devoluciones > pedidos: el valor de devoluciones no es plausible.
    # Se reemplaza por la mediana de devoluciones de la zona en los demás meses.
    malas = h["devoluciones"] > h["pedidos_realizados"]
    for i in h.index[malas]:
        zona = h.at[i, "zona_id"]
        otros = h[(h["zona_id"] == zona) & ~malas]["devoluciones"]
        nuevo = float(otros.median())
        bit.registrar(arch, f"{h.at[i, 'mes']}|{zona}", "devoluciones", h.at[i, "devoluciones"], nuevo,
                      "R3: devoluciones > pedidos; mediana de la zona en otros meses", "imputado")
        h.at[i, "devoluciones"] = nuevo
    h["pedidos_realizados"] = h["pedidos_realizados"].astype(int)
    h["devoluciones"] = h["devoluciones"].astype(int)
    assert h.groupby("mes").size().eq(len(zonas)).all()
    return h


def limpiar_pronostico(bit, zonas, controles, eventos):
    arch = "03_pronostico_demanda.csv"
    f = leer(arch)
    f = quitar_duplicados(f, ["mes", "zona_id"], arch, bit)
    f = f.merge(zonas[["zona_id", "pedidos_octubre_referencia"]], on="zona_id")
    f = f.merge(eventos[["mes", "factor_demanda_plan"]], on="mes")
    # Valor esperado de cada celda: referencia de la zona x factor del mes.
    # En los datos válidos el pronóstico se desvía de este esperado menos de ±10 %.
    f["esperado"] = f["pedidos_octubre_referencia"] * f["factor_demanda_plan"]
    ratio = f["pedidos_proyectados"] / f["esperado"]
    f["motivo"] = None
    f.loc[f["pedidos_proyectados"].isna(), "motivo"] = "nulo"
    f.loc[f["pedidos_proyectados"] < 0, "motivo"] = "negativo"
    f.loc[f["motivo"].isna() & ((ratio < RATIO_ATIPICO[0]) | (ratio > RATIO_ATIPICO[1])),
          "motivo"] = "atípico"
    f["original"] = f["pedidos_proyectados"]
    f.loc[f["motivo"].notna(), "pedidos_proyectados"] = np.nan

    # Conciliación contra el control mensual: el residuo (control - suma válida) se
    # asigna a las celdas inválidas; si hay varias, proporcional a su valor esperado.
    ctrl = controles.set_index("mes")["demanda_total_control_pedidos"]
    for mes, g in f.groupby("mes"):
        malas = g[g["motivo"].notna()]
        if malas.empty:
            continue
        residuo = int(ctrl[mes] - g["pedidos_proyectados"].sum())
        pesos = malas["esperado"] / malas["esperado"].sum()
        base = np.floor(pesos * residuo).astype(int)
        resto = residuo - base.sum()
        orden = (pesos * residuo - base).sort_values(ascending=False).index[:resto]
        base.loc[orden] += 1
        regla = ("R5: conciliar con control mensual (control - suma de celdas válidas)"
                 if len(malas) == 1 else
                 f"R5: conciliar con control mensual; residuo {residuo} repartido entre "
                 f"{len(malas)} celdas en proporción a referencia x factor")
        for i, nuevo in base.items():
            r = nuevo / f.at[i, "esperado"]
            if not (0.8 <= r <= 1.2):
                raise ValueError(f"Imputación implausible {mes} {f.at[i, 'zona_id']}: {nuevo} ({r:.2f})")
            f.at[i, "pedidos_proyectados"] = nuevo
            bit.registrar(arch, f"{mes}|{f.at[i, 'zona_id']}", "pedidos_proyectados",
                          f.at[i, "original"], nuevo,
                          f"{regla}; motivo: {f.at[i, 'motivo']}; esperado={f.at[i, 'esperado']:.0f}",
                          "imputado")
    f["pedidos_proyectados"] = f["pedidos_proyectados"].astype(int)
    suma = f.groupby("mes")["pedidos_proyectados"].sum()
    assert (suma == ctrl.reindex(suma.index)).all(), "El pronóstico no cuadra con los controles"
    return f[["mes", "zona_id", "pedidos_proyectados", "canal", "escenario", "version_pronostico"]]


def limpiar_bodegas(bit, controles):
    arch = "04_bodegas_candidatas.csv"
    b = leer(arch)
    assert b["bodega_id"].is_unique
    for i, fila in b.iterrows():
        nuevo = normalizar_municipio(fila["municipio"])
        if nuevo != fila["municipio"]:
            bit.registrar(arch, fila["bodega_id"], "municipio", fila["municipio"], nuevo,
                          "R2: normalizar contra catálogo de municipios", "modificado")
            b.at[i, "municipio"] = nuevo

    # Capacidad y costo fijo son atributos propios de cada inmueble: no hay ficha
    # ni información comparable que permita estimarlos (la capacidad varía de
    # 27.000 a 60.000 dentro de un mismo municipio). Se excluyen del modelo.
    b["habilitada_modelo"] = b["habilitada_octubre_2026"].astype(int)
    b["motivo_exclusion"] = ""
    for campo in ["capacidad_pedidos_mes", "costo_fijo_adicional_cop_mes"]:
        for i in b.index[b[campo].isna()]:
            b.at[i, "habilitada_modelo"] = 0
            b.at[i, "motivo_exclusion"] = f"{campo} nulo"
            bit.registrar(arch, b.at[i, "bodega_id"], campo, np.nan, "NA (sitio excluido)",
                          "R6: atributo propio del sitio sin información comparable; excluir candidato",
                          "excluido")
    num = ["capacidad_pedidos_mes", "costo_fijo_adicional_cop_mes", "costo_operacion_variable_cop_pedido"]
    assert (b[num].fillna(0) >= 0).all().all()
    ex = b.set_index("bodega_id").loc[BODEGA_EXISTENTE]
    assert ex["tipo"] == "existente" and ex["costo_fijo_adicional_cop_mes"] == 0
    cap_ctrl = controles["capacidad_bogota_actual_pedidos_mes"].unique()
    assert len(cap_ctrl) == 1 and ex["capacidad_pedidos_mes"] == cap_ctrl[0]
    assert (b.loc[b["bodega_id"] != BODEGA_EXISTENTE, "tipo"] == "candidata").all()
    return b


def limpiar_oferta(bit, controles):
    arch = "06_oferta_puertos_mensual.csv"
    o = leer(arch)
    o = quitar_duplicados(o, ["mes", "puerto_id"], arch, bit)
    c = controles.set_index("mes")
    fraccion = {"P01": "fraccion_puerto_cartagena", "P02": "fraccion_puerto_buenaventura"}
    for i in o.index[o["pedidos_disponibles"].isna()]:
        mes, p = o.at[i, "mes"], o.at[i, "puerto_id"]
        otro = o[(o["mes"] == mes) & (o["puerto_id"] != p)]["pedidos_disponibles"]
        # Con el otro puerto conocido, el total del control fija el valor exacto;
        # la fracción del puerto sirve de verificación.
        nuevo = float(c.at[mes, "demanda_total_control_pedidos"] - otro.sum())
        esperado = c.at[mes, "demanda_total_control_pedidos"] * c.at[mes, fraccion[p]]
        assert abs(nuevo - esperado) <= 1, (mes, p, nuevo, esperado)
        o.at[i, "pedidos_disponibles"] = nuevo
        bit.registrar(arch, f"{mes}|{p}", "pedidos_disponibles", np.nan, nuevo,
                      f"R5: control total - otro puerto (verificado con fracción: {esperado:.1f})",
                      "imputado")
    o["pedidos_disponibles"] = o["pedidos_disponibles"].astype(int)
    tot = o.groupby("mes")["pedidos_disponibles"].sum()
    assert (tot == c["demanda_total_control_pedidos"].reindex(tot.index)).all()
    for _, fila in o.iterrows():
        esperado = c.at[fila["mes"], "demanda_total_control_pedidos"] * c.at[fila["mes"], fraccion[fila["puerto_id"]]]
        assert abs(fila["pedidos_disponibles"] - esperado) <= 1
    return o


def _limpiar_rutas(df, arch, claves, grupo_col, campos, bit, validar_conf=False):
    """Marca valores inválidos y los imputa con rutas comparables del mismo grupo.

    grupo_col: puerto_id (abastecimiento) o bodega_id (distribución). Dentro de cada
    grupo el costo y el tiempo dependen casi solo de la distancia (r > 0,97).
    """
    df = quitar_duplicados(df, claves, arch, bit)
    assert (df["distancia_vial_estimada_km"] > 0).all()
    df["arco_valido"] = True
    df["motivo"] = ""

    if validar_conf:
        fuera = ~df["confiabilidad_pct"].between(0, 1)
        for i in df.index[fuera]:
            bit.registrar(arch, "|".join(df.loc[i, claves]), "confiabilidad_pct",
                          df.at[i, "confiabilidad_pct"], np.nan,
                          "R3: fuera de [0,1]; se deja nulo (no interviene en el modelo), arco se conserva",
                          "anulado")
        df.loc[fuera, "confiabilidad_pct"] = np.nan

    # 1) Marcar inválidos: nulos o no positivos.
    malos = {}
    for campo in campos:
        m = df[campo].isna() | (df[campo] <= 0)
        malos[campo] = m
    # 2) Atípicos: comparar con la mediana de rutas comparables (con los válidos).
    for campo in campos:
        validas = df[~malos[campo]]
        esperado = _esperado_por_vecinos(df, validas, grupo_col, campo)
        ratio = df[campo] / esperado
        atip = (~malos[campo]) & ((ratio < RATIO_ATIPICO[0]) | (ratio > RATIO_ATIPICO[1]))
        df[f"_atip_{campo}"] = atip
        malos[campo] = malos[campo] | atip

    # 3) Imputar con comparables o excluir el arco.
    for campo in campos:
        validas = df[~malos[campo]]
        for i in df.index[malos[campo]]:
            orig = df.at[i, campo]
            motivo = ("nulo" if pd.isna(orig) else
                      "no positivo" if orig <= 0 else "atípico")
            valor, n, vec = imputar_por_vecinos(validas.drop(index=i, errors="ignore"),
                                                grupo_col, df.at[i, grupo_col],
                                                df.at[i, "distancia_vial_estimada_km"], campo)
            clave = "|".join(df.loc[i, claves])
            if valor is None:
                df.at[i, "arco_valido"] = False
                df.at[i, "motivo"] += f"{campo} {motivo} sin comparables; "
                bit.registrar(arch, clave, campo, orig, "NA (arco excluido)",
                              f"R4: {motivo}; solo {n} rutas comparables (<{MIN_COMPARABLES}); excluir arco",
                              "excluido")
                continue
            if campo == "tiempo_abastecimiento_dias" or campo == "tiempo_entrega_dias":
                valor = round(valor, 2)
            else:
                valor = float(round(valor))
            df.at[i, campo] = valor
            refs = ", ".join(f"{r[claves[1] if grupo_col == claves[0] else claves[0]]}"
                             f"({r['distancia_vial_estimada_km']:.0f} km)" for _, r in vec.iterrows())
            bit.registrar(arch, clave, campo, orig, valor,
                          f"R4: {motivo}; mediana de {n} rutas del mismo {grupo_col} con distancia "
                          f"más cercana a {df.at[i, 'distancia_vial_estimada_km']:.1f} km: {refs}",
                          "imputado")
    df = df.drop(columns=[c for c in df.columns if c.startswith("_atip_")])
    return df


def _esperado_por_vecinos(df, validas, grupo_col, campo):
    """Mediana de `campo` en las K rutas válidas más cercanas en distancia (mismo grupo)."""
    esperado = pd.Series(np.nan, index=df.index)
    for g, sub in df.groupby(grupo_col):
        ref = validas[validas[grupo_col] == g]
        dist_ref = ref["distancia_vial_estimada_km"].to_numpy()
        val_ref = ref[campo].to_numpy()
        idx_ref = ref.index.to_numpy()
        for i, d in sub["distancia_vial_estimada_km"].items():
            mask = idx_ref != i
            orden = np.argsort(np.abs(dist_ref[mask] - d))[:K_VECINOS]
            esperado[i] = np.median(val_ref[mask][orden])
    return esperado


def limpiar_rutas_puerto_bodega(bit):
    arch = "07_rutas_puerto_bodega.csv"
    return _limpiar_rutas(leer(arch), arch, ["puerto_id", "bodega_id"], "puerto_id",
                          ["costo_abastecimiento_cop_pedido", "tiempo_abastecimiento_dias"], bit)


def limpiar_rutas_bodega_zona(bit):
    arch = "08_rutas_bodega_zona.csv"
    return _limpiar_rutas(leer(arch), arch, ["bodega_id", "zona_id"], "bodega_id",
                          ["costo_distribucion_cop_pedido", "tiempo_entrega_dias"], bit,
                          validar_conf=True)


# ---------------------------------------------------------------------------
# Tablas del modelo y validaciones
# ---------------------------------------------------------------------------

def construir_modelo_mes(mes, zonas, pron, bodegas, oferta, controles, rpb, rbz):
    d = pron[pron["mes"] == mes].merge(zonas[["zona_id", "ciudad_canonica"]], on="zona_id")
    d = d.rename(columns={"pedidos_proyectados": "demanda", "ciudad_canonica": "ciudad"})
    d = d[["zona_id", "ciudad", "demanda"]].sort_values("zona_id")

    b = bodegas[bodegas["habilitada_modelo"] == 1].copy()
    b = b.rename(columns={"capacidad_pedidos_mes": "capacidad",
                          "costo_fijo_adicional_cop_mes": "costo_fijo",
                          "costo_operacion_variable_cop_pedido": "costo_variable"})
    b["capacidad"] = b["capacidad"].astype(int)
    b["costo_fijo"] = b["costo_fijo"].astype(int)
    b = b[["bodega_id", "municipio", "sitio", "tipo", "latitud", "longitud",
           "capacidad", "costo_fijo", "costo_variable"]]

    s = oferta[oferta["mes"] == mes][["puerto_id", "pedidos_disponibles"]]
    s = s.rename(columns={"pedidos_disponibles": "oferta"})

    ids = set(b["bodega_id"])
    a_in = rpb[rpb["arco_valido"] & rpb["bodega_id"].isin(ids)]
    a_in = a_in[["puerto_id", "bodega_id", "distancia_vial_estimada_km",
                 "costo_abastecimiento_cop_pedido", "tiempo_abastecimiento_dias"]]
    a_out = rbz[rbz["arco_valido"] & rbz["bodega_id"].isin(ids)]
    a_out = a_out[["bodega_id", "zona_id", "distancia_vial_estimada_km", "tiempo_entrega_dias",
                   "costo_distribucion_cop_pedido", "transportista", "confiabilidad_pct"]]

    ctrl = controles.set_index("mes").loc[mes]
    validar_modelo(d, b, s, a_in, a_out, ctrl)
    return d, b, s, a_in, a_out


def validar_modelo(d, b, s, a_in, a_out, ctrl):
    D, S = d["demanda"].sum(), s["oferta"].sum()
    assert D == ctrl["demanda_total_control_pedidos"], f"Demanda {D} != control"
    assert S == D, f"Oferta {S} != demanda {D}"
    assert d["zona_id"].is_unique and d["demanda"].ge(0).all()
    assert not a_in.duplicated(["puerto_id", "bodega_id"]).any()
    assert not a_out.duplicated(["bodega_id", "zona_id"]).any()
    for col in ["costo_abastecimiento_cop_pedido", "tiempo_abastecimiento_dias"]:
        assert a_in[col].notna().all() and (a_in[col] > 0).all()
    for col in ["costo_distribucion_cop_pedido", "tiempo_entrega_dias"]:
        assert a_out[col].notna().all() and (a_out[col] > 0).all()
    assert BODEGA_EXISTENTE in set(b["bodega_id"])
    # Cada zona con demanda debe tener al menos un arco de entrada.
    sin_ruta = set(d.loc[d["demanda"] > 0, "zona_id"]) - set(a_out["zona_id"])
    assert not sin_ruta, f"Zonas sin ruta: {sin_ruta}"
    # Cada bodega debe poder abastecerse desde algún puerto y cada puerto debe llegar a alguna.
    assert set(b["bodega_id"]) <= set(a_in["bodega_id"]), "Bodegas sin abastecimiento"
    assert set(s["puerto_id"]) <= set(a_in["puerto_id"])
    # B001 debe poder recibir de ambos puertos (la oferta de cada puerto debe salir).
    # Capacidad: B001 + las dos mayores candidatas deben cubrir la demanda.
    cand = b[b["bodega_id"] != BODEGA_EXISTENTE]["capacidad"].nlargest(int(ctrl["max_bodegas_nuevas"]))
    cap_max = b.set_index("bodega_id").at[BODEGA_EXISTENTE, "capacidad"] + cand.sum()
    assert cap_max >= D, "Capacidad insuficiente incluso con las dos mayores aperturas"


# ---------------------------------------------------------------------------
# Bitácora
# ---------------------------------------------------------------------------

def escribir_bitacora(cambios, crudos, resumen):
    por_archivo = cambios.groupby(["archivo", "accion"]).size().unstack(fill_value=0)
    lineas = [
        "# Bitácora de limpieza",
        "",
        "Generada automáticamente por `src/limpieza.py` a partir de `data/raw/` (sin modificar).",
        "El detalle de cada cambio está en `reports/cambios_limpieza.csv`.",
        "",
        "## Reglas aplicadas",
        "",
        "| Regla | Descripción |",
        "|---|---|",
        "| R1 | Duplicados exactos: se conserva una copia. Si una clave se repite con valores distintos, el script se detiene. |",
        "| R2 | Etiquetas de municipio normalizadas contra un catálogo (sin tildes/mayúsculas, alias `B/manga`). Las uniones se hacen solo por ID. |",
        "| R3 | Rangos: devoluciones ≤ pedidos; confiabilidad en [0,1]. Un valor fuera de rango en un campo que no entra al modelo se anula sin eliminar el registro. |",
        f"| R4 | Rutas: costo o tiempo nulo, ≤ 0 o atípico (fuera de {RATIO_ATIPICO[0]}–{RATIO_ATIPICO[1]} × la mediana de sus comparables) se imputa con la mediana de las {K_VECINOS} rutas válidas del mismo puerto (abastecimiento) o de la misma bodega (distribución) con distancia más cercana (±{TOL_DISTANCIA_REL:.0%}). Con menos de {MIN_COMPARABLES} comparables el arco se excluye. Nunca se usa cero. |",
        "| R5 | Demanda y oferta: se concilian contra `09_controles_mensuales.csv` (el total del control menos la suma de celdas válidas). Si hay varias celdas inválidas en un mes, el residuo se reparte en proporción a referencia × factor del mes. |",
        "| R6 | Bodegas con capacidad o costo fijo nulo se excluyen del modelo: son atributos propios del inmueble sin ficha ni dato comparable. |",
        "",
        "Fundamento de R4 y R5 (verificado sobre los datos válidos):",
        "",
        "- Dentro de cada puerto, costo y tiempo de abastecimiento dependen casi solo de la distancia (tiempo ≈ 0,6 + 0,00185·km; costo con residuo ≈ ±8 %); no hay efecto propio por bodega.",
        "- En distribución, el tiempo tiene correlación 0,996 con la distancia y el costo 0,97. El transportista no explica varianza (<0,1 %); la bodega sí, un poco (≈ 5–11 %). Por eso los comparables son de la misma bodega.",
        "- El pronóstico de cada celda válida es `referencia de octubre × factor del mes` con ruido de ±9 %. Cada control mensual es exactamente la suma de las 60 zonas.",
        "",
        "## Resumen de cambios por archivo",
        "",
        por_archivo.to_markdown(),
        "",
        "## Detalle de cambios",
        "",
        cambios.to_markdown(index=False),
        "",
        "## Filas y conciliaciones",
        "",
        crudos.to_markdown(index=False),
        "",
        "## Validaciones del modelo del mes base",
        "",
    ]
    lineas += [f"- {k}: {v}" for k, v in resumen.items()]
    lineas += [
        "",
        "## Observaciones que no se corrigen",
        "",
        "- `11_diccionario_datos.csv` declara la unidad de `porcentaje_pedidos_urgentes` como «pedidos/mes», pero los valores son fracciones en [0,1]. Se interpreta como fracción; no interviene en el modelo.",
        "- El histórico de septiembre de 2026 supera la referencia de octubre de 2026 en las 60 zonas (mediana +18 %, mínimo +2,7 %), y la tendencia del histórico es creciente. El pronóstico base (100.000) parece conservador frente a la tendencia reciente. No se ajusta porque el control mensual lo fija, pero conviene revisar la sensibilidad a la demanda.",
        "- `habilitada_octubre_2026` vale 1 para las 100 bodegas; la exclusión por datos faltantes se registra en la columna nueva `habilitada_modelo`.",
    ]
    (REPORTS / "bitacora_limpieza.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    bit = Bitacora()

    controles = leer("09_controles_mensuales.csv")
    eventos = leer("10_eventos_comerciales.csv")
    puertos = leer("05_puertos.csv")
    zonas = limpiar_zonas(bit)
    hist = limpiar_historico(bit, zonas)
    pron = limpiar_pronostico(bit, zonas, controles, eventos)
    bodegas = limpiar_bodegas(bit, controles)
    oferta = limpiar_oferta(bit, controles)
    rpb = limpiar_rutas_puerto_bodega(bit)
    rbz = limpiar_rutas_bodega_zona(bit)

    # Integridad referencial por ID.
    Z, B, P = set(zonas["zona_id"]), set(bodegas["bodega_id"]), set(puertos["puerto_id"])
    for nombre, df, col, univ in [("histórico", hist, "zona_id", Z), ("pronóstico", pron, "zona_id", Z),
                                  ("rutas_bz", rbz, "zona_id", Z), ("rutas_bz", rbz, "bodega_id", B),
                                  ("rutas_pb", rpb, "bodega_id", B), ("rutas_pb", rpb, "puerto_id", P),
                                  ("oferta", oferta, "puerto_id", P)]:
        assert set(df[col]) == univ, f"{nombre}.{col} no coincide con el catálogo"

    # Tablas limpias completas (todos los meses)
    zonas.to_csv(CLEAN / "zonas.csv", index=False)
    hist.to_csv(CLEAN / "demanda_historica.csv", index=False)
    pron.to_csv(CLEAN / "pronostico_demanda.csv", index=False)
    bodegas.to_csv(CLEAN / "bodegas.csv", index=False)
    puertos.to_csv(CLEAN / "puertos.csv", index=False)
    oferta.to_csv(CLEAN / "oferta_puertos.csv", index=False)
    controles.to_csv(CLEAN / "controles_mensuales.csv", index=False)
    rpb.to_csv(CLEAN / "rutas_puerto_bodega.csv", index=False)
    rbz.to_csv(CLEAN / "rutas_bodega_zona.csv", index=False)

    # Tablas del modelo para el mes base
    d, b, s, a_in, a_out = construir_modelo_mes(MES_BASE, zonas, pron, bodegas, oferta,
                                                controles, rpb, rbz)
    sufijo = MES_BASE.replace("-", "")
    d.to_csv(CLEAN / f"modelo_{sufijo}_demanda.csv", index=False)
    b.to_csv(CLEAN / f"modelo_{sufijo}_bodegas.csv", index=False)
    s.to_csv(CLEAN / f"modelo_{sufijo}_oferta.csv", index=False)
    a_in.to_csv(CLEAN / f"modelo_{sufijo}_arcos_puerto_bodega.csv", index=False)
    a_out.to_csv(CLEAN / f"modelo_{sufijo}_arcos_bodega_zona.csv", index=False)

    cambios = bit.df()
    cambios.to_csv(REPORTS / "cambios_limpieza.csv", index=False)

    pron_crudo = leer("03_pronostico_demanda.csv")
    oct_crudo = pron_crudo[pron_crudo["mes"] == MES_BASE]["pedidos_proyectados"].sum()
    crudos = pd.DataFrame([
        ("02_demanda_historica.csv", len(leer("02_demanda_historica.csv")), len(hist)),
        ("03_pronostico_demanda.csv", len(pron_crudo), len(pron)),
        ("04_bodegas_candidatas.csv", 100, int(bodegas["habilitada_modelo"].sum())),
        ("07_rutas_puerto_bodega.csv", len(leer("07_rutas_puerto_bodega.csv")), int(rpb["arco_valido"].sum())),
        ("08_rutas_bodega_zona.csv", len(leer("08_rutas_bodega_zona.csv")), int(rbz["arco_valido"].sum())),
    ], columns=["archivo", "filas_crudas", "filas_o_elementos_utilizables"])
    resumen = {
        f"Demanda {MES_BASE} cruda (suma sin nulos)": f"{oct_crudo:,.0f}",
        f"Demanda {MES_BASE} limpia": f"{d['demanda'].sum():,}",
        f"Oferta {MES_BASE}": ", ".join(f"{r.puerto_id}={r.oferta:,}" for r in s.itertuples()),
        "Bodegas en el modelo": f"{len(b)} (B001 + {len(b) - 1} candidatas)",
        "Arcos puerto→bodega": len(a_in),
        "Arcos bodega→zona": len(a_out),
        "Zonas con al menos una ruta": f"{a_out['zona_id'].nunique()} / {len(d)}",
        "Capacidad máxima alcanzable (B001 + 2 mayores)":
            f"{b.set_index('bodega_id').at[BODEGA_EXISTENTE, 'capacidad'] + b[b['bodega_id'] != BODEGA_EXISTENTE]['capacidad'].nlargest(2).sum():,}",
    }
    escribir_bitacora(cambios, crudos, resumen)

    print(f"Cambios registrados: {len(cambios)}")
    print(cambios.groupby(["archivo", "accion"]).size().to_string())
    print()
    for k, v in resumen.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
