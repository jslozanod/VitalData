"""Arma la serie por hora de una IPS con calendario, clima y nivel reciente. Todo lo que entra como variable
estaba disponible a las 00:00 del dia que se pronostica (nada del futuro se cuela al entrenamiento)."""
from __future__ import annotations

import holidays
import numpy as np
import pandas as pd
from sqlalchemy import text

from vitaldata import config

FESTIVOS = holidays.CO(years=range(2019, 2031))


def cargar_horas(engine, ips: str, desde: str = config.INICIO_PERIODO_CONTINUO) -> pd.DataFrame:
    """Llegadas por hora desde la tabla agregada (incluye las horas sin llegadas como 0)."""
    q = text("""SELECT a.hora, a.llegadas, a.espera_media FROM vd.agg_llegadas_hora a
                JOIN vd.dim_ips i USING (ips_id) WHERE i.nombre = :n AND a.hora >= :d ORDER BY a.hora""")
    df = pd.read_sql(q, engine, params={"n": ips, "d": desde})
    return df


def cargar_clima(engine, desde: str = config.INICIO_PERIODO_CONTINUO) -> pd.DataFrame:
    q = text("""SELECT fecha, lluvia_mm, temp_media FROM vd.clima_diario WHERE estacion_id = :e AND fecha >= :d""")
    c = pd.read_sql(q, engine, params={"e": config.ESTACION_CLIMA, "d": desde})
    c["fecha"] = pd.to_datetime(c["fecha"])
    return c


def malla_horaria(horas: pd.DataFrame, fin: str | None = None) -> pd.DataFrame:
    """Rellena con 0 las horas sin llegadas y marca como dia faltante los dias sin ningun registro
    (la fuente tiene dias completos vacios que son fallas de registro, no dias sin pacientes)."""
    if horas.empty:
        return pd.DataFrame(columns=["hora", "llegadas", "dia_valido"])
    ini = horas["hora"].min().normalize()
    fin_ts = pd.Timestamp(fin) if fin else horas["hora"].max().normalize() + pd.Timedelta(hours=23)
    idx = pd.date_range(ini, fin_ts, freq="h")
    m = horas.set_index("hora").reindex(idx)
    m["llegadas"] = m["llegadas"].fillna(0).astype(int)
    m.index.name = "hora"
    m = m.reset_index()
    m["dia"] = m["hora"].dt.normalize()
    total_dia = m.groupby("dia")["llegadas"].transform("sum")
    m["dia_valido"] = total_dia > 0
    return m


def agregar_variables(m: pd.DataFrame, clima: pd.DataFrame | None, usar_clima: bool = True) -> pd.DataFrame:
    """Calendario, clima del dia y nivel reciente (promedio diario de los 7 dias validos anteriores)."""
    d = m.copy()
    d["hora_dia"] = d["hora"].dt.hour
    d["dow"] = d["hora"].dt.dayofweek
    d["es_festivo"] = d["dia"].dt.date.map(lambda x: x in FESTIVOS).astype(int)
    # tipo de dia: 0 = laboral, 1 = sabado, 2 = domingo o festivo
    d["tipo_dia"] = np.where((d["dow"] == 6) | (d["es_festivo"] == 1), 2, np.where(d["dow"] == 5, 1, 0))

    diario = d.groupby("dia").agg(total=("llegadas", "sum"), valido=("dia_valido", "first"))
    diario.loc[~diario["valido"].astype(bool), "total"] = np.nan
    nivel = diario["total"].shift(1).rolling(7, min_periods=3).mean()      # solo dias anteriores
    d["nivel_7d"] = d["dia"].map(nivel)
    d["log_nivel"] = np.log1p(d["nivel_7d"])

    if usar_clima and clima is not None and not clima.empty:
        c = clima.set_index("fecha")
        d["lluvia_mm"] = d["dia"].map(c["lluvia_mm"])
        d["temp_media"] = d["dia"].map(c["temp_media"])
        # dias sin dato de clima: se llenan con la mediana de la ventana para no perder el dia (y se marca)
        d["clima_faltante"] = d["lluvia_mm"].isna().astype(int)
        d["lluvia_mm"] = d["lluvia_mm"].fillna(d["lluvia_mm"].median()).fillna(0.0)
        d["temp_media"] = d["temp_media"].fillna(d["temp_media"].median()).fillna(d["temp_media"].mean()).fillna(13.0)
    else:
        d["lluvia_mm"] = 0.0
        d["temp_media"] = 0.0
        d["clima_faltante"] = 1
    d["log_lluvia"] = np.log1p(d["lluvia_mm"])
    return d


def preparar(engine, ips: str, usar_clima: bool = True, desde: str = config.INICIO_PERIODO_CONTINUO) -> pd.DataFrame:
    horas = cargar_horas(engine, ips, desde)
    clima = cargar_clima(engine, desde) if usar_clima else None
    return agregar_variables(malla_horaria(horas), clima, usar_clima)
