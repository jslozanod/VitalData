"""Reentrena, evalua en el periodo de prueba y publica: guarda metricas y pronosticos en PostgreSQL y el modelo final en disco."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import text

from vitaldata import config
from vitaldata.models import backtest, data, forecast

HIPER_RUTA = Path(__file__).with_name("hiperparametros.json")


def hiperparametros() -> dict:
    if HIPER_RUTA.exists():
        return json.loads(HIPER_RUTA.read_text(encoding="utf-8"))
    return {"alpha": 1e-3, "peso_reciente": 0.0}


def ips_modelables(engine) -> list[str]:
    q = text("""SELECT i.nombre FROM vd.dim_ips i JOIN vd.fact_atencion f USING (ips_id)
                GROUP BY i.nombre HAVING count(*) >= :m ORDER BY 1""")
    with engine.connect() as con:
        return [r[0] for r in con.execute(q, {"m": config.MIN_REGISTROS_IPS})]


def slug(ips: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in ips).strip("_")


def publicar_ips(engine, ips: str, etl_run_id: int | None = None, test_inicio: str = "2022-08-08") -> dict:
    hp = hiperparametros()
    d = data.preparar(engine, ips, usar_clima=True)
    res = backtest.correr(engine, ips, test_inicio=test_inicio, alpha=hp["alpha"], peso_reciente=hp["peso_reciente"], d=d)
    pred: pd.DataFrame = res["pred"]

    # modelo final: ajustado con todo lo disponible, para el escenario "que pasaria si"
    final = forecast.ajustar(d, usar_clima=True, alpha=hp["alpha"], peso_reciente=hp["peso_reciente"])
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, config.MODELS_DIR / f"{slug(ips)}.joblib")

    with engine.begin() as con:
        ips_id = con.execute(text("SELECT ips_id FROM vd.dim_ips WHERE nombre = :n"), {"n": ips}).scalar_one()
        con.execute(text("UPDATE vd.model_run SET vigente = FALSE WHERE ips_id = :i"), {"i": ips_id})
        params = {"hiperparametros": hp, "coeficientes_no_perfil": {
            c: round(float(v), 4) for c, v in zip(final.columnas, final.modelo.coef_)
            if not c.startswith("h") or c in ("log_nivel",)}, "sobredispersion_alfa": round(final.alfa_disp, 4),
            "mejor_referencia": res["mejor_referencia"]}
        mid = con.execute(text("""INSERT INTO vd.model_run (ips_id, algoritmo, train_desde, train_hasta, test_desde, test_hasta,
                                  metricas, parametros, etl_run_id)
                                  VALUES (:i, 'poisson_glm_v1', :td, :th, :sd, :sh, CAST(:m AS jsonb), CAST(:p AS jsonb), :e)
                                  RETURNING model_run_id"""),
                          {"i": ips_id, "td": d["hora"].min().to_pydatetime(), "th": pd.Timestamp(test_inicio).to_pydatetime(),
                           "sd": pred["hora"].min().to_pydatetime(), "sh": pred["hora"].max().to_pydatetime(),
                           "m": json.dumps({"metricas": res["metricas"], "vs_referencia_3h": res["vs_referencia_3h"],
                                            "vs_referencia_dia": res["vs_referencia_dia"], "dias_evaluados": res["dias_evaluados"],
                                            "horas_evaluadas": res["horas_evaluadas"]}),
                           "p": json.dumps(params), "e": etl_run_id}).scalar_one()
        for modelo, col in (("vitaldata", "vitaldata"), ("vitaldata_sin_clima", "vitaldata_sin_clima"),
                            ("b_media_4s", "b_media_4s"), ("b_semana_anterior", "b_semana_anterior"), ("b_nivel", "b_nivel")):
            f = pd.DataFrame({"model_run_id": mid, "ips_id": ips_id, "hora": pred["hora"], "modelo": modelo,
                              "prediccion": pred[col].astype(float), "real": pred["real"].astype(int)})
            if modelo == "vitaldata":
                f["lo80"], f["hi80"] = pred["lo80"].astype(float), pred["hi80"].astype(float)
            else:
                f["lo80"], f["hi80"] = None, None
            f.to_sql("forecast_hora", con, schema="vd", if_exists="append", index=False, method="multi", chunksize=2000)
    return {"ips": ips, "model_run_id": mid, "metricas": res["metricas"], "vs_ref_3h": res["vs_referencia_3h"],
            "vs_ref_dia": res["vs_referencia_dia"], "mejor_referencia": res["mejor_referencia"]}


def publicar_todo(engine, etl_run_id: int | None = None) -> list[dict]:
    return [publicar_ips(engine, i, etl_run_id) for i in ips_modelables(engine)]
