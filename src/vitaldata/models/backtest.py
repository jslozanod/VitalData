"""Validacion con ventana que avanza (rolling-origin): cada semana se vuelve a ajustar el modelo solo con lo que
ya habia pasado y se pronostican los dias siguientes. Asi el periodo de prueba nunca se usa para entrenar."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from vitaldata.models import baselines, data, forecast

MODELOS = ["vitaldata", "vitaldata_sin_clima", "b_media_4s", "b_semana_anterior", "b_nivel"]


def wape(y: np.ndarray, p: np.ndarray) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    s = y.sum()
    return float(np.abs(y - p).sum() / s) if s > 0 else float("nan")


def _bloques(pred: pd.DataFrame, nivel: str) -> pd.DataFrame:
    p = pred.copy()
    p["dia"] = p["hora"].dt.normalize()
    if nivel == "hora":
        return p
    clave = ["dia", p["hora"].dt.hour // 3] if nivel == "3h" else ["dia"]
    cols = ["real"] + [m for m in MODELOS if m in p.columns]
    return p.groupby(clave)[cols].sum().reset_index(drop=True)


def metricas(pred: pd.DataFrame) -> dict:
    out: dict = {}
    for nivel in ("hora", "3h", "dia"):
        b = _bloques(pred, nivel)
        out[nivel] = {}
        for m in MODELOS:
            if m not in b.columns:
                continue
            w = wape(b["real"], b[m])
            out[nivel][m] = {"wape": round(w, 4), "precision": round(1 - w, 4),
                             "mae": round(float(np.abs(b["real"] - b[m]).mean()), 3)}
    if {"lo80", "hi80"} <= set(pred.columns):
        dentro = (pred["real"] >= pred["lo80"]) & (pred["real"] <= pred["hi80"])
        out["cobertura_80"] = round(float(dentro.mean()), 4)
    return out


def diferencia_bootstrap(pred: pd.DataFrame, modelo: str, referencia: str, nivel: str = "3h",
                         n: int = 2000, semilla: int = 7) -> dict:
    """Remuestrea dias completos y calcula cuanto baja el WAPE del modelo frente a la referencia."""
    rng = np.random.default_rng(semilla)
    p = pred.copy()
    p["dia"] = p["hora"].dt.normalize()
    dias = p["dia"].unique()
    partes = {d: g for d, g in p.groupby("dia")}
    difs = []
    for _ in range(n):
        muestra = pd.concat([partes[d] for d in rng.choice(dias, size=len(dias), replace=True)])
        b = _bloques(muestra.assign(hora=muestra["hora"]), nivel) if nivel != "dia" else \
            muestra.groupby("dia")[["real", modelo, referencia]].sum().reset_index(drop=True)
        difs.append(wape(b["real"], b[referencia]) - wape(b["real"], b[modelo]))
    difs = np.array(difs)
    return {"mejora_media": round(float(difs.mean()), 4), "ic95": [round(float(np.percentile(difs, 2.5)), 4),
            round(float(np.percentile(difs, 97.5)), 4)], "prob_modelo_mejor": round(float((difs > 0).mean()), 4)}


def correr(engine, ips: str, test_inicio: str = "2022-08-08", paso_dias: int = 7,
           alpha: float = 1e-3, peso_reciente: float = 0.0, test_fin: str | None = None,
           con_sin_clima: bool = True, d: pd.DataFrame | None = None) -> dict:
    d = data.preparar(engine, ips, usar_clima=True) if d is None else d.copy()
    if d.empty:
        raise ValueError(f"No hay datos para {ips}")
    d["b_semana_anterior"] = baselines.mismo_dia_semana_anterior(d)
    d["b_media_4s"] = baselines.media_4_semanas(d)
    d["b_nivel"] = baselines.nivel_constante(d)
    t0 = pd.Timestamp(test_inicio)
    fin = pd.Timestamp(test_fin) if test_fin else d["hora"].max()
    partes = []
    ini = t0
    while ini <= fin:
        sig = ini + pd.Timedelta(days=paso_dias)
        train = d[d["hora"] < ini]
        bloque = d[(d["hora"] >= ini) & (d["hora"] < sig) & (d["hora"] <= fin + pd.Timedelta(hours=23))]
        bloque = bloque[bloque["dia_valido"] & bloque["nivel_7d"].notna()
                        & bloque[["b_semana_anterior", "b_media_4s"]].notna().all(axis=1)]
        if len(bloque):
            m_c = forecast.ajustar(train, usar_clima=True, alpha=alpha, peso_reciente=peso_reciente)
            m_s = forecast.ajustar(train, usar_clima=False, alpha=alpha, peso_reciente=peso_reciente) if con_sin_clima else None
            mu = m_c.predecir(bloque)
            lo, hi = m_c.intervalo(mu)
            partes.append(pd.DataFrame({
                "hora": bloque["hora"].values, "real": bloque["llegadas"].values, "vitaldata": mu,
                "vitaldata_sin_clima": m_s.predecir(bloque) if m_s is not None else np.nan, "lo80": lo, "hi80": hi,
                "b_semana_anterior": bloque["b_semana_anterior"].values,
                "b_media_4s": bloque["b_media_4s"].values, "b_nivel": bloque["b_nivel"].values,
            }))
        ini = sig
    pred = pd.concat(partes, ignore_index=True)
    if not con_sin_clima:
        pred = pred.drop(columns=["vitaldata_sin_clima"])
    met = metricas(pred)
    mejor_ref = min(("b_media_4s", "b_semana_anterior", "b_nivel"), key=lambda m: met["3h"][m]["wape"])
    return {"ips": ips, "pred": pred, "metricas": met, "mejor_referencia": mejor_ref,
            "vs_referencia_3h": diferencia_bootstrap(pred, "vitaldata", mejor_ref, "3h"),
            "vs_referencia_dia": diferencia_bootstrap(pred, "vitaldata", mejor_ref, "dia"),
            "ventana_prueba": [str(pred["hora"].min()), str(pred["hora"].max())], "dias_evaluados": int(pred["hora"].dt.normalize().nunique()),
            "horas_evaluadas": int(len(pred))}


def a_json(res: dict) -> str:
    return json.dumps({k: v for k, v in res.items() if k != "pred"}, ensure_ascii=False, indent=2, default=str)
