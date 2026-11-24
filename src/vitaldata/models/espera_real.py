"""Lo que muestran los datos reales sobre la espera: relacion con la carga de la hora y perfil por hora del dia."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import text

BINS = [0, 1, 2, 3, 4, 6, 1000]
ETIQ = ["1", "2", "3", "4", "5-6", "7 o mas"]


def espera_por_carga(engine, ips: str, desde: str = "2021-04-01") -> list[dict]:
    """Espera media (con intervalo de confianza) segun cuantas personas llegaron en esa misma hora."""
    q = text("""SELECT a.llegadas, a.espera_media FROM vd.agg_llegadas_hora a JOIN vd.dim_ips i USING (ips_id)
                WHERE i.nombre = :n AND a.hora >= :d AND a.espera_media IS NOT NULL""")
    d = pd.read_sql(q, engine, params={"n": ips, "d": desde})
    return resumir_carga(d)


def resumir_carga(d: pd.DataFrame) -> list[dict]:
    if d.empty:
        return []
    d = d.copy()
    d["grupo"] = pd.cut(d["llegadas"], BINS, labels=ETIQ, right=True)
    out = []
    for g, x in d.groupby("grupo", observed=True):
        n = len(x)
        media = float(x["espera_media"].mean())
        ee = float(x["espera_media"].std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
        out.append({"llegadas_en_la_hora": str(g), "horas": int(n), "espera_media_min": round(media, 1),
                    "ic95": [round(media - 1.96 * ee, 1), round(media + 1.96 * ee, 1)]})
    return out


def correlacion_carga_espera(engine, ips: str, desde: str = "2021-04-01") -> dict:
    q = text("""SELECT a.llegadas, a.espera_media FROM vd.agg_llegadas_hora a JOIN vd.dim_ips i USING (ips_id)
                WHERE i.nombre = :n AND a.hora >= :d AND a.espera_media IS NOT NULL""")
    d = pd.read_sql(q, engine, params={"n": ips, "d": desde})
    if len(d) < 30:
        return {"n_horas": int(len(d)), "spearman": None}
    rho = float(d["llegadas"].corr(d["espera_media"], method="spearman"))
    # prueba de permutacion: cuantas veces una correlacion al azar iguala a la observada
    rng = np.random.default_rng(11)
    perm = np.array([pd.Series(rng.permutation(d["espera_media"].values)).corr(d["llegadas"], method="spearman")
                     for _ in range(500)])
    return {"n_horas": int(len(d)), "spearman": round(rho, 3), "p_permutacion": round(float((np.abs(perm) >= abs(rho)).mean()), 4)}


def espera_tipica(engine, ips: str, hora_dia: int, tipo_dia: str = "laboral", dia_semana: int | None = None) -> float | None:
    """Espera media historica de esa IPS a esa hora, para el tipo de dia (laboral, sabado, domingo).
    Si se pasa `dia_semana` (0 = lunes ... 6 = domingo) se usa ese dia exacto y no el tipo."""
    dows = str(int(dia_semana)) if dia_semana is not None else {"laboral": "0,1,2,3,4", "sabado": "5", "domingo": "6"}.get(tipo_dia, "0,1,2,3,4")
    q = text(f"""SELECT avg(f.espera_min) FROM vd.fact_atencion f JOIN vd.dim_ips i USING (ips_id)
                 WHERE i.nombre = :n AND extract(hour FROM f.ingreso) = :h
                   AND extract(isodow FROM f.ingreso)::int - 1 IN ({dows}) AND f.ingreso >= '2022-01-01'""")
    with engine.connect() as con:
        v = con.execute(q, {"n": ips, "h": int(hora_dia)}).scalar()
    return None if v is None else round(float(v), 1)


def espera_tipica_por_dia(engine, dia_semana: int) -> list[dict]:
    """Espera media por hora de cada IPS en un dia de la semana exacto (0 = lunes ... 6 = domingo), con el numero de atenciones."""
    q = text("""SELECT i.nombre AS ips, i.red, extract(hour FROM f.ingreso)::int AS h, avg(f.espera_min) AS w, count(*) AS n
                FROM vd.fact_atencion f JOIN vd.dim_ips i USING (ips_id)
                WHERE extract(isodow FROM f.ingreso)::int - 1 = :d AND f.ingreso >= '2022-01-01'
                GROUP BY i.nombre, i.red, extract(hour FROM f.ingreso)""")
    with engine.connect() as con:
        filas = con.execute(q, {"d": int(dia_semana)}).all()
    por: dict[str, dict] = {}
    for r in filas:
        c = por.setdefault(r.ips, {"ips": r.ips, "red": r.red, "horas": [{"hora": h, "espera_min": None, "atenciones": 0} for h in range(24)]})
        c["horas"][r.h] = {"hora": r.h, "espera_min": round(float(r.w), 1), "atenciones": int(r.n)}
    return list(por.values())
