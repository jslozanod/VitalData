import numpy as np
import pandas as pd
import pytest

from tests.helpers import serie_sintetica
from vitaldata.models import baselines, data, forecast


def test_el_nivel_reciente_no_usa_el_futuro():
    d = serie_sintetica()
    d2 = d[["hora", "llegadas", "dia", "dia_valido"]].copy()
    d2.loc[d2["dia"] >= pd.Timestamp("2021-06-20"), "llegadas"] = 999            # se cambia el futuro
    a = data.agregar_variables(d2, None, usar_clima=False)
    antes = d["dia"] <= pd.Timestamp("2021-06-20")           # incluso el propio 20 usa solo los dias anteriores
    assert np.allclose(d.loc[antes, "nivel_7d"].fillna(-1), a.loc[antes, "nivel_7d"].fillna(-1))


def test_dias_sin_registro_no_cuentan_como_cero():
    d = serie_sintetica()
    horas = d[["hora", "llegadas"]].copy()
    horas = horas[horas["hora"].dt.date != pd.Timestamp("2021-06-01").date()]
    horas = horas[horas["llegadas"] > 0]
    m = data.malla_horaria(horas)
    assert m.loc[m["dia"] == "2021-06-01", "dia_valido"].eq(False).all()


def test_ajuste_recupera_el_perfil_dia_noche():
    d = serie_sintetica(dias=90)
    m = forecast.ajustar(d.iloc[: 24 * 70], usar_clima=False)
    prueba = d.iloc[24 * 70:]
    mu = m.predecir(prueba)
    dia = prueba["hora_dia"].between(7, 18).values
    assert mu[dia].mean() == pytest.approx(4.0, rel=0.15)
    assert mu[~dia].mean() == pytest.approx(0.8, rel=0.3)


def test_pocos_dias_es_error():
    with pytest.raises(ValueError):
        forecast.ajustar(serie_sintetica(dias=10), usar_clima=False)


def test_predicciones_nunca_son_negativas_ni_nan():
    d = serie_sintetica()
    mu = forecast.ajustar(d, usar_clima=False).predecir(forecast.validas(d))
    assert np.isfinite(mu).all() and (mu >= 0).all()


def test_intervalo_contiene_la_prediccion():
    d = serie_sintetica()
    m = forecast.ajustar(d, usar_clima=False)
    mu = m.predecir(forecast.validas(d))
    lo, hi = m.intervalo(mu)
    assert (lo <= np.ceil(mu)).all() and (hi >= np.floor(mu)).all()


def test_sklearn_y_statsmodels_coinciden():
    """Verificacion cruzada: dos librerias, el mismo ajuste."""
    d = serie_sintetica(dias=60)
    sk = forecast.ajustar(d, usar_clima=False, alpha=1e-8).predecir(forecast.validas(d))
    sm = forecast.ajustar_statsmodels(d, usar_clima=False)
    assert np.max(np.abs(sk - sm)) < 0.02


def test_referencias_usan_solo_el_pasado():
    d = serie_sintetica()
    b = baselines.mismo_dia_semana_anterior(d)
    assert b.iloc[: 24 * 7].isna().all()
    assert b.iloc[24 * 7] == d["llegadas"].iloc[0]
