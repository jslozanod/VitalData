import numpy as np
import pandas as pd

from vitaldata.models import data


def serie_sintetica(dias=70, semilla=3, nivel=4.0):
    """Llegadas Poisson con perfil por hora conocido: mas de dia que de noche."""
    rng = np.random.default_rng(semilla)
    idx = pd.date_range("2021-05-03", periods=dias * 24, freq="h")
    perfil = np.where((idx.hour >= 7) & (idx.hour <= 18), nivel, nivel * 0.2)
    df = pd.DataFrame({"hora": idx, "llegadas": rng.poisson(perfil)})
    df["dia"] = df["hora"].dt.normalize()
    df["dia_valido"] = True
    return data.agregar_variables(df, None, usar_clima=False)
