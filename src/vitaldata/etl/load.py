"""Carga a PostgreSQL: dimensiones, hechos (idempotente por huella), agregado por hora, clima y auditoria."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from vitaldata import config
from vitaldata.etl.validate import Issue

SCHEMA_SQL = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or config.DATABASE_URL, pool_pre_ping=True, future=True)


def init_schema(engine: Engine) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with engine.begin() as con:
        con.exec_driver_sql(sql.replace("%", "%%"))


def iniciar_corrida(engine: Engine, flujo: str) -> int:
    with engine.begin() as con:
        return con.execute(text("INSERT INTO vd.etl_run (flujo) VALUES (:f) RETURNING etl_run_id"),
                           {"f": flujo}).scalar_one()


def cerrar_corrida(engine: Engine, run_id: int, estado: str, **cifras) -> None:
    detalle = cifras.pop("detalle", None)
    with engine.begin() as con:
        con.execute(text("""
            UPDATE vd.etl_run SET fin = now(), estado = :estado, filas_extraidas = :ex, filas_duplicadas = :du,
                   filas_rechazadas = :re, filas_corregidas = :co, filas_cargadas = :ca,
                   detalle = CAST(:det AS jsonb)
            WHERE etl_run_id = :id"""),
            {"estado": estado, "ex": cifras.get("extraidas"), "du": cifras.get("duplicadas"),
             "re": cifras.get("rechazadas"), "co": cifras.get("corregidas"), "ca": cifras.get("cargadas"),
             "det": json.dumps(detalle, ensure_ascii=False, default=str) if detalle else None, "id": run_id})


def guardar_issues(engine: Engine, run_id: int, issues: list[Issue]) -> None:
    if not issues:
        return
    with engine.begin() as con:
        for i in issues:
            con.execute(text("""INSERT INTO vd.dq_issue (etl_run_id, regla, severidad, filas, accion, ejemplo)
                                VALUES (:r, :regla, :sev, :f, :a, CAST(:ej AS jsonb))"""),
                        {"r": run_id, "regla": i.regla, "sev": i.severidad, "f": i.filas, "a": i.accion,
                         "ej": json.dumps(i.ejemplo, ensure_ascii=False, default=str) if i.ejemplo else None})


def cargar_atenciones(engine: Engine, df: pd.DataFrame, run_id: int) -> int:
    """Inserta solo lo nuevo. La huella unica hace que correr el ETL dos veces no duplique filas."""
    if df.empty:
        return 0
    ips = df[["ips", "red", "nom_admini"]].drop_duplicates("ips").rename(columns={"nom_admini": "entidad"})
    with engine.begin() as con:
        for r in ips.itertuples(index=False):
            con.execute(text("""INSERT INTO vd.dim_ips (nombre, red, entidad) VALUES (:n, :r, :e)
                                ON CONFLICT (nombre) DO UPDATE SET red = EXCLUDED.red, entidad = EXCLUDED.entidad"""),
                        {"n": r.ips, "r": r.red, "e": r.entidad})
        con.exec_driver_sql("""CREATE TEMP TABLE stg_atencion (ips TEXT, triage_id SMALLINT, ingreso TIMESTAMP,
                               atencion TIMESTAMP, espera_min REAL, huella CHAR(32)) ON COMMIT DROP""")
        buf = io.StringIO()
        df[["ips", "triage_id", "ingreso", "atencion", "espera_min", "huella"]].to_csv(buf, index=False, header=False)
        buf.seek(0)
        cur = con.connection.cursor()
        cur.copy_expert("COPY stg_atencion FROM STDIN WITH (FORMAT csv)", buf)
        res = con.execute(text("""
            INSERT INTO vd.fact_atencion (ips_id, triage_id, ingreso, atencion, espera_min, huella, etl_run_id)
            SELECT i.ips_id, s.triage_id, s.ingreso, s.atencion, s.espera_min, s.huella, :run
            FROM stg_atencion s JOIN vd.dim_ips i ON i.nombre = s.ips
            ON CONFLICT (huella) DO NOTHING"""), {"run": run_id})
        return res.rowcount


def refrescar_agregado(engine: Engine) -> int:
    with engine.begin() as con:
        con.exec_driver_sql("TRUNCATE vd.agg_llegadas_hora")
        res = con.exec_driver_sql("""
            INSERT INTO vd.agg_llegadas_hora (ips_id, hora, llegadas, espera_media, espera_p90)
            SELECT ips_id, date_trunc('hour', ingreso) AS hora, COUNT(*),
                   AVG(espera_min)::real, (percentile_cont(0.9) WITHIN GROUP (ORDER BY espera_min))::real
            FROM vd.fact_atencion GROUP BY ips_id, date_trunc('hour', ingreso)""")
        return res.rowcount


def cargar_clima(engine: Engine, estacion: dict, diario: pd.DataFrame) -> int:
    with engine.begin() as con:
        con.execute(text("""INSERT INTO vd.dim_estacion (estacion_id, nombre, municipio, latitud, longitud)
                            VALUES (:id, :n, :m, :la, :lo)
                            ON CONFLICT (estacion_id) DO UPDATE SET nombre = EXCLUDED.nombre"""),
                    {"id": estacion["id"], "n": estacion["nombre"], "m": estacion["municipio"],
                     "la": estacion.get("latitud"), "lo": estacion.get("longitud")})
        n = 0
        for r in diario.itertuples(index=False):
            con.execute(text("""INSERT INTO vd.clima_diario (estacion_id, fecha, lluvia_mm, temp_media, temp_max, temp_min, n_lluvia, n_temp)
                                VALUES (:e, :f, :ll, :tm, :tx, :tn, :nl, :nt)
                                ON CONFLICT (estacion_id, fecha) DO UPDATE SET lluvia_mm = EXCLUDED.lluvia_mm,
                                   temp_media = EXCLUDED.temp_media, temp_max = EXCLUDED.temp_max,
                                   temp_min = EXCLUDED.temp_min, n_lluvia = EXCLUDED.n_lluvia, n_temp = EXCLUDED.n_temp"""),
                        {"e": estacion["id"], "f": r.fecha, "ll": _n(r.lluvia_mm), "tm": _n(r.temp_media),
                         "tx": _n(r.temp_max), "tn": _n(r.temp_min), "nl": _i(r.n_lluvia), "nt": _i(r.n_temp)})
            n += 1
        return n


def _n(v):
    return None if v is None or pd.isna(v) else float(v)


def _i(v):
    return None if v is None or pd.isna(v) else int(v)
