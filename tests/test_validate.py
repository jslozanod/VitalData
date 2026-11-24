import pandas as pd
import pytest

from vitaldata.etl import validate


def test_columnas_obligatorias(crudo_pequeno):
    with pytest.raises(validate.SchemaError):
        validate.validar(crudo_pequeno.drop(columns=["triage"]))


def test_reglas_sobre_filas_conocidas(crudo_pequeno):
    r = validate.validar(crudo_pequeno)
    assert r.extraidas == 10
    assert r.duplicadas == 1
    assert r.corregidas == 1                       # la espera de -0.5 min pasa a 0
    assert r.rechazadas == 4                       # atencion antes, triage IX, fecha mala, mas de 24 h
    assert len(r.datos) == 10 - 1 - 4
    assert (r.datos["espera_min"] >= 0).all()
    assert (r.datos["atencion"] >= r.datos["ingreso"]).all()
    reglas = {i.regla: i.filas for i in r.issues}
    assert reglas["fila_duplicada_exacta"] == 1
    assert reglas["espera_negativa_por_redondeo"] == 1
    assert reglas["triage_no_valido"] == 1
    assert reglas["fecha_no_valida"] == 1


def test_nada_se_pierde_sin_explicacion(crudo_pequeno):
    r = validate.validar(crudo_pequeno)
    assert r.extraidas == len(r.datos) + r.duplicadas + r.rechazadas


def test_dataframe_vacio():
    r = validate.validar(pd.DataFrame(columns=validate.COLUMNAS_REQUERIDAS))
    assert r.datos.empty and r.issues[0].regla == "sin_filas"


def test_limite_exacto_de_24_horas():
    base = {"fecha_ing": "2021-05-03T00:00:00", "triage": "III", "ips": "X"}
    exacto = pd.DataFrame([{**base, "fecha_atencion": "2021-05-04T00:00:00"}])       # 1440 min: se acepta
    de_mas = pd.DataFrame([{**base, "fecha_atencion": "2021-05-04T00:01:00"}])       # 1441 min: se rechaza
    assert len(validate.validar(exacto).datos) == 1
    assert len(validate.validar(de_mas).datos) == 0


def test_fecha_en_el_futuro_se_rechaza():
    df = pd.DataFrame([{"fecha_ing": "2099-01-01T00:00:00", "fecha_atencion": "2099-01-01T00:10:00", "triage": "III", "ips": "X"}])
    r = validate.validar(df)
    assert len(r.datos) == 0 and r.rechazadas == 1


def test_triage_en_minusculas_y_con_espacios():
    df = pd.DataFrame([{"fecha_ing": "2021-05-03T00:00:00", "fecha_atencion": "2021-05-03T00:10:00", "triage": " iii ", "ips": " hospital x "}])
    r = validate.validar(df)
    assert r.datos.iloc[0]["triage_id"] == 3 and r.datos.iloc[0]["ips"] == "HOSPITAL X"


def test_huella_estable():
    a = pd.Series({"codadminis": "A", "fecha_ing": "2021-01-01T00:00:00.1", "triage": "III", "ips": "X"})
    assert validate.huella_fila(a) == validate.huella_fila(a.copy())
    b = a.copy()
    b["triage"] = "IV"
    assert validate.huella_fila(a) != validate.huella_fila(b)
