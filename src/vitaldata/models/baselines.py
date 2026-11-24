"""Referencias sin inteligencia artificial. Si el modelo no las supera, no sirve."""
from __future__ import annotations

import numpy as np
import pandas as pd


def mismo_dia_semana_anterior(d: pd.DataFrame) -> pd.Series:
    """Prediccion = llegadas de la misma hora, 7 dias antes."""
    return d["llegadas"].shift(24 * 7)


def media_4_semanas(d: pd.DataFrame) -> pd.Series:
    """Prediccion = promedio de la misma hora del mismo dia de la semana en las 4 semanas anteriores."""
    cols = [d["llegadas"].shift(24 * 7 * k) for k in (1, 2, 3, 4)]
    return pd.concat(cols, axis=1).mean(axis=1, skipna=False)


def nivel_constante(d: pd.DataFrame) -> pd.Series:
    """Prediccion = promedio de llegadas por hora de los 7 dias anteriores (ignora hora y dia)."""
    return d["nivel_7d"] / 24.0
