"""Pruebas de integracion del ETL contra PostgreSQL real (base vitaldata_test, separada de los datos reales)."""
import pandas as pd
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from vitaldata.etl import extract, load, pipeline

pytestmark = pytest.mark.integration


@pytest.fixture()
def csv_pequeno(tmp_path, crudo_pequeno):
    ruta = tmp_path / "triage.csv"
    crudo_pequeno.to_csv(ruta, index=False)
    return ruta


def _limpiar(eng):
    with eng.begin() as con:
        con.exec_driver_sql("TRUNCATE vd.fact_atencion, vd.agg_llegadas_hora, vd.dq_issue, vd.etl_run RESTART IDENTITY CASCADE")


def test_carga_completa_y_conciliacion(engine_prueba, csv_pequeno):
    _limpiar(engine_prueba)
    r = pipeline.flujo_triage(engine_prueba, desde_archivo=csv_pequeno)
    assert (r["extraidas"], r["duplicadas"], r["rechazadas"], r["corregidas"], r["cargadas"]) == (10, 1, 4, 1, 5)
    with engine_prueba.connect() as con:
        assert con.execute(text("SELECT count(*) FROM vd.fact_atencion")).scalar() == 5
        # conciliacion: extraidas - duplicadas - rechazadas = filas en la tabla de hechos
        assert 10 - 1 - 4 == 5
        estado = con.execute(text("SELECT estado FROM vd.etl_run WHERE etl_run_id = :i"), {"i": r["run_id"]}).scalar()
        assert estado == "ok"
        reglas = {x[0] for x in con.execute(text("SELECT regla FROM vd.dq_issue WHERE etl_run_id = :i"), {"i": r["run_id"]})}
        assert {"fila_duplicada_exacta", "espera_negativa_por_redondeo", "triage_no_valido", "fecha_no_valida"} <= reglas


def test_el_agregado_por_hora_suma_lo_mismo_que_los_hechos(engine_prueba, csv_pequeno):
    _limpiar(engine_prueba)
    pipeline.flujo_triage(engine_prueba, desde_archivo=csv_pequeno)
    with engine_prueba.connect() as con:
        a = con.execute(text("SELECT sum(llegadas) FROM vd.agg_llegadas_hora")).scalar()
        b = con.execute(text("SELECT count(*) FROM vd.fact_atencion")).scalar()
    assert a == b


def test_correr_dos_veces_no_duplica(engine_prueba, csv_pequeno):
    _limpiar(engine_prueba)
    pipeline.flujo_triage(engine_prueba, desde_archivo=csv_pequeno)
    r2 = pipeline.flujo_triage(engine_prueba, desde_archivo=csv_pequeno)
    assert r2["cargadas"] == 0
    with engine_prueba.connect() as con:
        assert con.execute(text("SELECT count(*) FROM vd.fact_atencion")).scalar() == 5


def test_la_base_rechaza_atencion_antes_del_ingreso(engine_prueba):
    with engine_prueba.begin() as con:
        con.execute(text("INSERT INTO vd.dim_ips (nombre) VALUES ('X') ON CONFLICT DO NOTHING"))
    with pytest.raises(IntegrityError):
        with engine_prueba.begin() as con:
            con.execute(text("""INSERT INTO vd.fact_atencion (ips_id, triage_id, ingreso, atencion, espera_min, huella)
                                SELECT ips_id, 3, '2021-05-03 10:00', '2021-05-03 09:00', 0, 'a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1'
                                FROM vd.dim_ips WHERE nombre = 'X'"""))


def test_la_base_rechaza_triage_inexistente_y_espera_enorme(engine_prueba):
    with pytest.raises(IntegrityError):
        with engine_prueba.begin() as con:
            con.execute(text("""INSERT INTO vd.fact_atencion (ips_id, triage_id, ingreso, atencion, espera_min, huella)
                                SELECT ips_id, 9, '2021-05-03 10:00', '2021-05-03 10:10', 10, 'b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2'
                                FROM vd.dim_ips WHERE nombre = 'X'"""))
    with pytest.raises(IntegrityError):
        with engine_prueba.begin() as con:
            con.execute(text("""INSERT INTO vd.fact_atencion (ips_id, triage_id, ingreso, atencion, espera_min, huella)
                                SELECT ips_id, 3, '2021-05-03 10:00', '2021-05-05 10:10', 3000, 'c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3'
                                FROM vd.dim_ips WHERE nombre = 'X'"""))


def test_integridad_referencial_de_hechos(engine_prueba):
    with pytest.raises(IntegrityError):
        with engine_prueba.begin() as con:
            con.execute(text("""INSERT INTO vd.fact_atencion (ips_id, triage_id, ingreso, atencion, espera_min, huella)
                                VALUES (9999, 3, '2021-05-03 10:00', '2021-05-03 10:10', 10, 'd4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4')"""))


def test_una_falla_de_extraccion_queda_registrada(engine_prueba, monkeypatch):
    _limpiar(engine_prueba)

    def falla(*a, **k):
        raise extract.ExtractError("API caida")
    monkeypatch.setattr(extract, "extraer_triage", falla)
    with pytest.raises(extract.ExtractError):
        pipeline.flujo_triage(engine_prueba, cliente=object())
    with engine_prueba.connect() as con:
        estado, det = con.execute(text("SELECT estado, detalle FROM vd.etl_run ORDER BY etl_run_id DESC LIMIT 1")).one()
    assert estado == "error" and "API caida" in det["error"]


def test_clima_con_dias_sin_dato(engine_prueba):
    lluvia = pd.DataFrame({"dia": ["2021-05-03T00:00:00", "2021-05-04T00:00:00"], "lluvia_mm": ["5.2", "0"], "n": ["144", "40"]})
    temp = pd.DataFrame({"dia": ["2021-05-03T00:00:00"], "temp_media": ["14.5"], "temp_max": ["18"], "temp_min": ["10"], "n": ["5"]})
    d = pipeline.armar_clima_diario(lluvia, temp)
    assert d.loc[d["fecha"].astype(str) == "2021-05-03", "lluvia_mm"].iloc[0] == 5.2
    assert pd.isna(d.loc[d["fecha"].astype(str) == "2021-05-04", "lluvia_mm"].iloc[0])       # 40 observaciones: no es confiable
    n = load.cargar_clima(engine_prueba, {"id": "T1", "nombre": "Prueba", "municipio": "PASTO"}, d)
    assert n == 2
