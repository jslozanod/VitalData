"""Validacion y limpieza de las atenciones de urgencias.

Cada regla deja constancia de cuantas filas toco y que se hizo con ellas: nada se borra en silencio.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import pandas as pd

from vitaldata import config

COLUMNAS_REQUERIDAS = ["fecha_ing", "fecha_atencion", "triage", "ips"]
COLUMNAS_CRUDAS = ["codadminis", "nom_admini", "fecha_ing", "hora_ingre", "fecha_atencion", "hora_atencion",
                   "triage", "ips", "red"]
TRIAGE_A_ID = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
ESPERA_MAXIMA_MIN = 1440
TOPE_REGISTRADO_MIN = 360


class SchemaError(ValueError):
    pass


@dataclass
class Issue:
    regla: str
    severidad: str          # info | aviso | error
    filas: int
    accion: str
    ejemplo: dict | None = None


@dataclass
class Resultado:
    datos: pd.DataFrame
    issues: list[Issue] = field(default_factory=list)
    extraidas: int = 0
    duplicadas: int = 0
    rechazadas: int = 0
    corregidas: int = 0


def huella_fila(fila: pd.Series) -> str:
    """md5 de la fila cruda completa (con milisegundos). Dos filas identicas dan la misma huella."""
    texto = "|".join("" if pd.isna(fila.get(c)) else str(fila.get(c)) for c in COLUMNAS_CRUDAS)
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def _ej(df: pd.DataFrame, n: int = 2) -> dict | None:
    if df.empty:
        return None
    return {"filas_de_ejemplo": df.head(n).astype(str).to_dict("records")}


def validar(crudo: pd.DataFrame, ahora: pd.Timestamp | None = None) -> Resultado:
    faltan = [c for c in COLUMNAS_REQUERIDAS if c not in crudo.columns]
    if faltan:
        raise SchemaError(f"Faltan columnas obligatorias: {faltan}")

    res = Resultado(datos=pd.DataFrame(), extraidas=len(crudo))
    if crudo.empty:
        res.issues.append(Issue("sin_filas", "aviso", 0, "no hay nada que cargar"))
        return res

    df = crudo.copy()
    for c in COLUMNAS_CRUDAS:
        if c not in df.columns:
            df[c] = None
    ahora = ahora or pd.Timestamp.now()

    # 1) huella y duplicados exactos (la fuente trae filas insertadas dos veces con el mismo milisegundo)
    df["huella"] = df.apply(huella_fila, axis=1)
    dup = df.duplicated("huella", keep="first")
    res.duplicadas = int(dup.sum())
    if res.duplicadas:
        res.issues.append(Issue("fila_duplicada_exacta", "aviso", res.duplicadas,
                                "se conserva una sola copia", _ej(df[dup])))
    df = df[~dup].copy()

    # 2) fechas
    df["ingreso"] = pd.to_datetime(df["fecha_ing"], errors="coerce")
    df["atencion"] = pd.to_datetime(df["fecha_atencion"], errors="coerce")
    malas = df["ingreso"].isna() | df["atencion"].isna()
    if malas.any():
        res.issues.append(Issue("fecha_no_valida", "error", int(malas.sum()), "fila rechazada", _ej(df[malas])))
        res.rechazadas += int(malas.sum())
        df = df[~malas].copy()

    fuera = (df["ingreso"] < pd.Timestamp("2015-01-01")) | (df["ingreso"] > ahora + pd.Timedelta(days=1))
    if fuera.any():
        res.issues.append(Issue("fecha_fuera_de_rango", "error", int(fuera.sum()), "fila rechazada", _ej(df[fuera])))
        res.rechazadas += int(fuera.sum())
        df = df[~fuera].copy()

    # 3) triage
    df["triage_norm"] = df["triage"].astype(str).str.strip().str.upper()
    sin_triage = ~df["triage_norm"].isin(TRIAGE_A_ID)
    if sin_triage.any():
        res.issues.append(Issue("triage_no_valido", "error", int(sin_triage.sum()), "fila rechazada", _ej(df[sin_triage])))
        res.rechazadas += int(sin_triage.sum())
        df = df[~sin_triage].copy()
    df["triage_id"] = df["triage_norm"].map(TRIAGE_A_ID).astype("int16")

    # 4) IPS
    df["ips_norm"] = df["ips"].astype(str).str.strip().str.upper()
    sin_ips = df["ips_norm"].isin(["", "NAN", "NONE"])
    if sin_ips.any():
        res.issues.append(Issue("ips_vacia", "error", int(sin_ips.sum()), "fila rechazada", _ej(df[sin_ips])))
        res.rechazadas += int(sin_ips.sum())
        df = df[~sin_ips].copy()

    # 5) espera = atencion - ingreso
    df["espera_min"] = (df["atencion"] - df["ingreso"]).dt.total_seconds() / 60.0
    redondeo = (df["espera_min"] < 0) & (df["espera_min"] >= -1.0)
    if redondeo.any():
        res.issues.append(Issue("espera_negativa_por_redondeo", "aviso", int(redondeo.sum()),
                                "la atencion se registro con menos de un minuto de diferencia: espera = 0",
                                _ej(df[redondeo])))
        res.corregidas += int(redondeo.sum())
        df.loc[redondeo, "espera_min"] = 0.0
        df.loc[redondeo, "atencion"] = df.loc[redondeo, "ingreso"]   # la fuente recorta la atencion al minuto
    negativa = df["espera_min"] < 0
    if negativa.any():
        res.issues.append(Issue("espera_negativa", "error", int(negativa.sum()), "fila rechazada", _ej(df[negativa])))
        res.rechazadas += int(negativa.sum())
        df = df[~negativa].copy()
    larga = df["espera_min"] > ESPERA_MAXIMA_MIN
    if larga.any():
        res.issues.append(Issue("espera_mayor_a_24h", "error", int(larga.sum()), "fila rechazada", _ej(df[larga])))
        res.rechazadas += int(larga.sum())
        df = df[~larga].copy()
    tope = df["espera_min"] >= TOPE_REGISTRADO_MIN
    if tope.any():
        res.issues.append(Issue("espera_en_tope_de_360_min", "info", int(tope.sum()),
                                "se conserva; la fuente parece cortar la espera en 6 horas (dato censurado)"))

    res.datos = df[["ips_norm", "triage_id", "ingreso", "atencion", "espera_min", "huella", "red", "nom_admini"]] \
        .rename(columns={"ips_norm": "ips"}).reset_index(drop=True)

    # 6) IPS con pocos registros: se cargan, pero no se modelan
    conteo = res.datos["ips"].value_counts()
    pocas = conteo[conteo < config.MIN_REGISTROS_IPS]
    if len(pocas):
        res.issues.append(Issue("ips_con_pocos_registros", "info", int(pocas.sum()),
                                f"se cargan, pero no se modelan (menos de {config.MIN_REGISTROS_IPS} atenciones)",
                                {"ips": {k: int(v) for k, v in pocas.items()}}))
    return res
