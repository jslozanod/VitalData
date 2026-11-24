"""Tareas del flujo diario. Cada una es una funcion pequena para que Airflow las ejecute por separado
y para poder probarlas sin Airflow."""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import text

from vitaldata import config
from vitaldata.etl import extract, load, pipeline

log = logging.getLogger("vitaldata.tareas")


class ControlFallido(RuntimeError):
    pass


def verificar_fuente() -> dict:
    """La fuente debe seguir existiendo y no debe tener MENOS filas de las que ya leimos (si encoge, algo cambio)."""
    cliente = extract.SocrataClient()
    r = cliente.get(config.DS_TRIAGE, {"$select": "count(*) as n, max(fecha_ing) as ultimo"})[0]
    n_fuente = int(r["n"])
    eng = load.get_engine()
    with eng.connect() as con:
        ultimo = con.execute(text("""SELECT filas_extraidas FROM vd.etl_run WHERE flujo = 'triage_urgencias' AND estado = 'ok'
                                     AND filas_extraidas > 0 AND detalle->>'incremental' IS DISTINCT FROM 'true' ORDER BY etl_run_id DESC LIMIT 1""")).scalar()
    log.info("Filas en la fuente: %s (ultima lectura completa: %s)", n_fuente, ultimo)
    if ultimo is not None and n_fuente < ultimo:
        raise ControlFallido(f"La fuente tiene {n_fuente} filas y la ultima lectura completa trajo {ultimo}")
    return {"filas_fuente": n_fuente, "ultimo_ingreso": r.get("ultimo")}


def triage_incremental() -> dict:
    eng = load.get_engine()
    load.init_schema(eng)
    with eng.connect() as con:
        ultimo = con.execute(text("SELECT max(ingreso) FROM vd.fact_atencion")).scalar()
    desde = None if ultimo is None else (pd.Timestamp(ultimo) - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    log.info("Carga %s", "completa" if desde is None else f"incremental desde {desde} (con 7 dias de traslape)")
    return pipeline.flujo_triage(eng, desde=desde)


def clima_reciente() -> dict:
    """Trae el clima de los ultimos 30 dias ya cargados hasta el mes siguiente a la ultima atencion (el clima solo
    hace falta donde hay llegadas que explicar)."""
    eng = load.get_engine()
    with eng.connect() as con:
        ultimo = con.execute(text("SELECT max(fecha) FROM vd.clima_diario")).scalar()
        ult_atencion = con.execute(text("SELECT max(ingreso) FROM vd.fact_atencion")).scalar()
    desde = "2020-01-01" if ultimo is None else (pd.Timestamp(ultimo) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    tope = pd.Timestamp(ult_atencion) if ult_atencion is not None else pd.Timestamp("2022-10-01")
    hasta = (tope + pd.offsets.MonthBegin(1)).strftime("%Y-%m-01")
    return pipeline.flujo_clima(eng, desde=desde, hasta=hasta)


def controles_de_calidad() -> dict:
    """Comprobaciones que deben cumplirse despues de cada carga. Si una falla, el flujo se detiene aqui."""
    eng = load.get_engine()
    resultados: dict = {}
    with eng.connect() as con:
        hechos = con.execute(text("SELECT count(*) FROM vd.fact_atencion")).scalar()
        agregado = con.execute(text("SELECT coalesce(sum(llegadas), 0) FROM vd.agg_llegadas_hora")).scalar()
        resultados["hechos_igual_agregado"] = bool(hechos == agregado)
        resultados["sin_atencion_antes_de_ingreso"] = con.execute(text(
            "SELECT count(*) FROM vd.fact_atencion WHERE atencion < ingreso")).scalar() == 0
        resultados["sin_huellas_repetidas"] = con.execute(text(
            "SELECT count(*) FROM (SELECT huella FROM vd.fact_atencion GROUP BY huella HAVING count(*) > 1) x")).scalar() == 0
        resultados["ultima_corrida_ok"] = con.execute(text(
            "SELECT estado FROM vd.etl_run WHERE flujo = 'triage_urgencias' ORDER BY etl_run_id DESC LIMIT 1")).scalar() == "ok"
        resultados["hay_clima"] = con.execute(text("SELECT count(*) FROM vd.clima_diario WHERE lluvia_mm IS NOT NULL")).scalar() > 100
    malos = [k for k, v in resultados.items() if not v]
    log.info("Controles: %s", resultados)
    if malos:
        raise ControlFallido(f"Fallaron los controles: {malos}")
    return resultados


def publicar() -> list[dict]:
    from vitaldata.models import publicar as pub
    eng = load.get_engine()
    res = pub.publicar_todo(eng)
    return [{"ips": r["ips"], "model_run_id": r["model_run_id"], "precision_3h": r["metricas"]["3h"]["vitaldata"]["precision"],
             "mejor_referencia_3h": r["metricas"]["3h"][r["mejor_referencia"]]["precision"]} for r in res]


def compuerta_del_modelo(tolerancia: float = 0.0) -> dict:
    """Puerta de calidad: el modelo no se publica como vigente si pierde contra la mejor referencia en la mayoria de IPS."""
    eng = load.get_engine()
    with eng.connect() as con:
        filas = con.execute(text("""SELECT i.nombre, m.metricas->'metricas'->'3h'->'vitaldata'->>'wape' AS w,
                                    m.parametros->>'mejor_referencia' AS ref, m.metricas->'metricas'->'3h' AS t
                                    FROM vd.model_run m JOIN vd.dim_ips i USING (ips_id) WHERE m.vigente""")).all()
    if not filas:
        raise ControlFallido("No hay modelos vigentes")
    gana = 0
    for nombre, w, ref, t in filas:
        if float(w) <= float(t[ref]["wape"]) + tolerancia:
            gana += 1
    if gana < (len(filas) + 1) // 2:
        raise ControlFallido(f"El modelo solo supera a la referencia en {gana} de {len(filas)} IPS")
    return {"ips_donde_gana": gana, "ips_total": len(filas)}


def exportar_snapshot() -> dict:
    from vitaldata import export
    return export.snapshot(load.get_engine(), config.ROOT / "web" / "data")
