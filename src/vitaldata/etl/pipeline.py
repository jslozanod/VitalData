"""Flujos del ETL. Los usa el script de linea de comandos, las pruebas y el DAG de Airflow."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from vitaldata import config
from vitaldata.etl import extract, load, validate

log = logging.getLogger("vitaldata.etl")
MIN_OBS_LLUVIA_DIA = 100
MIN_OBS_TEMP_DIA = 3


def flujo_triage(engine, cliente: extract.SocrataClient | None = None, desde: str | None = None,
                 desde_archivo: Path | None = None) -> dict:
    """Extrae -> valida -> carga -> refresca el agregado. Registra la corrida aunque falle."""
    run_id = load.iniciar_corrida(engine, "triage_urgencias")
    try:
        if desde_archivo is not None:
            crudo = pd.read_csv(desde_archivo, dtype=str)
        else:
            cliente = cliente or extract.SocrataClient()
            filas = extract.extraer_triage(cliente, desde)
            crudo = pd.DataFrame(filas)
            config.RAW_DIR.mkdir(parents=True, exist_ok=True)
            if not crudo.empty and desde is None:
                crudo.to_csv(config.RAW_DIR / "pasto_triage_urgencias_raw.csv", index=False)
        log.info("Extraidas %s filas", len(crudo))
        res = validate.validar(crudo)
        load.guardar_issues(engine, run_id, res.issues)
        cargadas = load.cargar_atenciones(engine, res.datos, run_id)
        horas = load.refrescar_agregado(engine)
        cifras = dict(extraidas=res.extraidas, duplicadas=res.duplicadas, rechazadas=res.rechazadas,
                      corregidas=res.corregidas, cargadas=cargadas,
                      detalle={"validas": len(res.datos), "horas_en_agregado": horas, "incremental": desde is not None})
        load.cerrar_corrida(engine, run_id, "ok", **cifras)
        return {"run_id": run_id, **cifras}
    except Exception as e:  # se registra y se vuelve a lanzar para que Airflow marque la tarea en rojo
        load.cerrar_corrida(engine, run_id, "error", detalle={"error": f"{type(e).__name__}: {e}"})
        raise


def flujo_clima(engine, cliente: extract.SocrataClient | None = None, desde: str = "2020-01-01",
                hasta: str = "2022-10-01") -> dict:
    run_id = load.iniciar_corrida(engine, "clima_ideam")
    try:
        cliente = cliente or extract.SocrataClient()
        est = config.ESTACION_CLIMA
        lluvia = pd.DataFrame(extract.extraer_clima_diario(cliente, config.DS_LLUVIA, est, desde, hasta,
                                                           "sum(valorobservado) as lluvia_mm"))
        temp = pd.DataFrame(extract.extraer_clima_diario(
            cliente, config.DS_TEMP, est, desde, hasta,
            "avg(valorobservado) as temp_media, max(valorobservado) as temp_max, min(valorobservado) as temp_min"))
        diario = armar_clima_diario(lluvia, temp)
        info = cliente.get(config.DS_LLUVIA, {"codigoestacion": est, "$limit": 1})
        estacion = {"id": est, "nombre": (info[0]["nombreestacion"] if info else est).strip(),
                    "municipio": "PASTO", "latitud": float(info[0]["latitud"]) if info else None,
                    "longitud": float(info[0]["longitud"]) if info else None}
        n = load.cargar_clima(engine, estacion, diario)
        load.cerrar_corrida(engine, run_id, "ok", extraidas=len(lluvia) + len(temp), cargadas=n)
        return {"run_id": run_id, "dias": n}
    except Exception as e:
        load.cerrar_corrida(engine, run_id, "error", detalle={"error": f"{type(e).__name__}: {e}"})
        raise


def armar_clima_diario(lluvia: pd.DataFrame, temp: pd.DataFrame) -> pd.DataFrame:
    """Une lluvia y temperatura por dia. Un dia con pocas observaciones queda vacio en vez de inventar un valor."""
    def prep(df, cols):
        if df.empty:
            return pd.DataFrame(columns=["fecha", "n"] + cols)
        df = df.copy()
        df["fecha"] = pd.to_datetime(df["dia"]).dt.date
        for c in cols + ["n"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    ll = prep(lluvia, ["lluvia_mm"]).rename(columns={"n": "n_lluvia"})[["fecha", "lluvia_mm", "n_lluvia"]]
    tp = prep(temp, ["temp_media", "temp_max", "temp_min"]).rename(columns={"n": "n_temp"})[
        ["fecha", "temp_media", "temp_max", "temp_min", "n_temp"]]
    out = ll.merge(tp, on="fecha", how="outer").sort_values("fecha").reset_index(drop=True)
    # lluvia: observaciones cada 10 minutos (hasta 144 por dia); temperatura: pocas lecturas por dia
    out.loc[out["n_lluvia"].fillna(0) < MIN_OBS_LLUVIA_DIA, "lluvia_mm"] = pd.NA
    out.loc[out["n_temp"].fillna(0) < MIN_OBS_TEMP_DIA, ["temp_media", "temp_max", "temp_min"]] = pd.NA
    return out
