"""Modelo de VitalData: regresion de Poisson por hora con perfil por tipo de dia, clima y nivel reciente.

Se escribe dos veces a proposito: con scikit-learn (el que se usa) y con statsmodels (sin penalizacion). Si las dos
dan casi lo mismo, el ajuste no depende de una libreria concreta.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import PoissonRegressor

FEATURES_CLIMA = ["log_lluvia", "temp_estandar"]


def matriz(d: pd.DataFrame, usar_clima: bool, temp_mu: float, temp_sd: float, nivel_mu: float = 0.0) -> pd.DataFrame:
    """Columnas: perfil hora x tipo de dia (72), dia de la semana, nivel reciente y, si se pide, clima."""
    X = pd.DataFrame(index=d.index)
    for t in (0, 1, 2):
        for h in range(24):
            X[f"h{h:02d}_t{t}"] = ((d["hora_dia"] == h) & (d["tipo_dia"] == t)).astype(float)
    for k in range(1, 5):                       # lunes (0) es la referencia de la semana laboral; martes..viernes
        X[f"dow{k}"] = (d["dow"] == k).astype(float)
    X["log_nivel"] = (d["log_nivel"] - nivel_mu).astype(float)      # centrado: el perfil por hora ya hace de intercepto
    if usar_clima:
        X["log_lluvia"] = d["log_lluvia"].astype(float)
        X["temp_estandar"] = ((d["temp_media"] - temp_mu) / (temp_sd if temp_sd > 0 else 1.0)).astype(float)
    return X


@dataclass
class ModeloPoisson:
    usar_clima: bool
    modelo: PoissonRegressor
    columnas: list[str]
    temp_mu: float
    temp_sd: float
    nivel_mu: float
    alfa_disp: float                            # sobredispersion (binomial negativa)

    def predecir(self, d: pd.DataFrame) -> np.ndarray:
        X = matriz(d, self.usar_clima, self.temp_mu, self.temp_sd, self.nivel_mu)[self.columnas]
        return self.modelo.predict(X.values)

    def intervalo(self, mu: np.ndarray, nivel: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
        lo_q, hi_q = (1 - nivel) / 2, 1 - (1 - nivel) / 2
        mu = np.asarray(mu, dtype=float)
        if self.alfa_disp <= 1e-9:
            return stats.poisson.ppf(lo_q, mu), stats.poisson.ppf(hi_q, mu)
        r = 1.0 / self.alfa_disp
        p = r / (r + mu)
        return stats.nbinom.ppf(lo_q, r, p), stats.nbinom.ppf(hi_q, r, p)


def validas(d: pd.DataFrame) -> pd.DataFrame:
    return d[d["dia_valido"] & d["nivel_7d"].notna()]


def ajustar(train: pd.DataFrame, usar_clima: bool = True, alpha: float = 1e-3, peso_reciente: float = 0.0,
            ventana_disp_dias: int = 56) -> ModeloPoisson:
    """peso_reciente > 0 da mas peso a los dias cercanos (decae con la antiguedad, en dias).
    La sobredispersion se estima con los ultimos `ventana_disp_dias` dias, que reflejan el regimen actual."""
    t = validas(train)
    if len(t) < 24 * 14:
        raise ValueError("Se necesitan al menos 14 dias validos para ajustar el modelo")
    temp_mu, temp_sd = float(t["temp_media"].mean()), float(t["temp_media"].std() or 1.0)
    nivel_mu = float(t["log_nivel"].mean())
    X = matriz(t, usar_clima, temp_mu, temp_sd, nivel_mu)
    w = None
    if peso_reciente > 0:
        edad = (t["dia"].max() - t["dia"]).dt.days.values
        w = np.exp(-peso_reciente * edad)
    m = PoissonRegressor(alpha=alpha, fit_intercept=False, max_iter=300, tol=1e-6)
    m.fit(X.values, t["llegadas"].values, sample_weight=w)
    reciente = (t["dia"] > t["dia"].max() - pd.Timedelta(days=ventana_disp_dias)).values
    mu = m.predict(X.values[reciente])
    y = t["llegadas"].values[reciente]
    # sobredispersion por momentos: Var = mu + alfa * mu^2
    alfa = max(0.0, float(np.sum((y - mu) ** 2 - mu) / np.sum(mu ** 2)))
    return ModeloPoisson(usar_clima, m, list(X.columns), temp_mu, temp_sd, nivel_mu, alfa)


def ajustar_statsmodels(train: pd.DataFrame, usar_clima: bool = True) -> np.ndarray:
    """Misma especificacion sin penalizacion, con statsmodels. Devuelve las predicciones en el propio train."""
    import statsmodels.api as sm
    t = validas(train)
    temp_mu, temp_sd = float(t["temp_media"].mean()), float(t["temp_media"].std() or 1.0)
    X = matriz(t, usar_clima, temp_mu, temp_sd, float(t["log_nivel"].mean()))
    X = X.loc[:, (X != 0).any()]                 # columnas que nunca ocurren
    glm = sm.GLM(t["llegadas"].values, X.values, family=sm.families.Poisson()).fit(maxiter=200)
    return glm.predict(X.values)
