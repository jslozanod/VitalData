import numpy as np
import pandas as pd
import pytest

from tests.helpers import serie_sintetica
from vitaldata.models import backtest


def test_wape_casos_conocidos():
    assert backtest.wape([10, 10], [10, 10]) == 0.0
    assert backtest.wape([10, 10], [0, 0]) == 1.0
    assert backtest.wape([10, 10], [12, 8]) == pytest.approx(0.2)
    assert np.isnan(backtest.wape([0, 0], [1, 1]))          # sin llegadas reales no hay error porcentual


def test_metricas_agrupan_por_franja_y_por_dia():
    horas = pd.date_range("2022-08-08", periods=48, freq="h")
    pred = pd.DataFrame({"hora": horas, "real": 1, "vitaldata": 1.0, "b_media_4s": 2.0, "b_semana_anterior": 1.0, "b_nivel": 0.5})
    m = backtest.metricas(pred)
    assert m["hora"]["vitaldata"]["wape"] == 0.0 and m["hora"]["b_media_4s"]["wape"] == 1.0
    assert m["dia"]["b_nivel"]["wape"] == 0.5
    assert m["3h"]["vitaldata"]["precision"] == 1.0


def test_cobertura_del_intervalo():
    horas = pd.date_range("2022-08-08", periods=10, freq="h")
    pred = pd.DataFrame({"hora": horas, "real": [1] * 10, "vitaldata": 1.0, "lo80": [0] * 8 + [2, 2], "hi80": [3] * 10})
    assert backtest.metricas(pred)["cobertura_80"] == 0.8


def test_bootstrap_detecta_un_modelo_mejor():
    horas = pd.date_range("2022-08-08", periods=24 * 20, freq="h")
    rng = np.random.default_rng(1)
    real = rng.poisson(3, len(horas))
    pred = pd.DataFrame({"hora": horas, "real": real, "vitaldata": real + rng.normal(0, 0.3, len(horas)), "malo": rng.poisson(3, len(horas)) * 1.0})
    r = backtest.diferencia_bootstrap(pred, "vitaldata", "malo", "dia", n=200)
    assert r["prob_modelo_mejor"] > 0.95 and r["ic95"][0] > 0


def test_correr_con_serie_sintetica_gana_a_la_referencia_sin_ia():
    d = serie_sintetica(dias=110, nivel=4.0)
    ini = (d["hora"].min() + pd.Timedelta(days=88)).strftime("%Y-%m-%d")
    r = backtest.correr(None, "SINTETICA", test_inicio=ini, d=d)
    assert r["dias_evaluados"] >= 14
    m = r["metricas"]
    assert 0 < m["3h"]["vitaldata"]["precision"] <= 1
    assert m["3h"]["vitaldata"]["wape"] <= m["3h"]["b_nivel"]["wape"]          # el perfil por hora le gana a un nivel plano
    assert 0.5 < m["cobertura_80"] <= 1
    assert set(r["pred"].columns) >= {"hora", "real", "vitaldata", "lo80", "hi80"}
    assert '"ips": "SINTETICA"' in backtest.a_json(r)


def test_no_se_usa_el_periodo_de_prueba_para_entrenar():
    """Si se cambian las llegadas del periodo de prueba, los pronosticos de la primera semana no pueden cambiar."""
    d = serie_sintetica(dias=110)
    ini = d["hora"].min() + pd.Timedelta(days=88)
    d2 = d.copy()
    d2.loc[d2["hora"] >= ini + pd.Timedelta(days=7), "llegadas"] = 50       # solo se altera lo que viene despues de la primera semana
    a = backtest.correr(None, "S", test_inicio=ini.strftime("%Y-%m-%d"), d=d, con_sin_clima=False)["pred"]
    b = backtest.correr(None, "S", test_inicio=ini.strftime("%Y-%m-%d"), d=d2, con_sin_clima=False)["pred"]
    sem1 = a["hora"] < ini + pd.Timedelta(days=7)
    assert np.allclose(a.loc[sem1, "vitaldata"].values, b[b["hora"] < ini + pd.Timedelta(days=7)]["vitaldata"].values)
