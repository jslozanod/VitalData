"""Tareas del flujo diario y exportacion, probadas contra PostgreSQL (base de pruebas y, para exportar, la real)."""
import json

import pandas as pd
import pytest
from sqlalchemy import text

from vitaldata.etl import extract, load, pipeline, tareas

pytestmark = pytest.mark.integration


@pytest.fixture()
def base_cargada(engine_prueba, tmp_path, crudo_pequeno, monkeypatch):
    with engine_prueba.begin() as con:
        con.exec_driver_sql("TRUNCATE vd.fact_atencion, vd.agg_llegadas_hora, vd.dq_issue, vd.etl_run, vd.model_run RESTART IDENTITY CASCADE")
    ruta = tmp_path / "t.csv"
    crudo_pequeno.to_csv(ruta, index=False)
    pipeline.flujo_triage(engine_prueba, desde_archivo=ruta)
    with engine_prueba.begin() as con:
        con.execute(text("""INSERT INTO vd.dim_estacion VALUES ('E1', 'Prueba', 'PASTO', 1.0, -77.0) ON CONFLICT DO NOTHING"""))
        con.execute(text("""INSERT INTO vd.clima_diario (estacion_id, fecha, lluvia_mm)
                            SELECT 'E1', d::date, 1.0 FROM generate_series('2021-01-01'::date, '2021-06-01'::date, '1 day') d
                            ON CONFLICT DO NOTHING"""))
    monkeypatch.setattr(load, "get_engine", lambda url=None: engine_prueba)
    return engine_prueba


def test_controles_pasan_con_datos_sanos(base_cargada):
    r = tareas.controles_de_calidad()
    assert all(r.values())


def test_controles_detectan_un_agregado_roto(base_cargada):
    with base_cargada.begin() as con:
        con.exec_driver_sql("DELETE FROM vd.agg_llegadas_hora")
    with pytest.raises(tareas.ControlFallido, match="hechos_igual_agregado"):
        tareas.controles_de_calidad()


def _modelo(con, wape_modelo, wape_ref):
    ips = con.execute(text("SELECT ips_id FROM vd.dim_ips LIMIT 1")).scalar()
    m = {"metricas": {"3h": {"vitaldata": {"wape": wape_modelo}, "b_media_4s": {"wape": wape_ref}}}}
    con.execute(text("""INSERT INTO vd.model_run (ips_id, algoritmo, metricas, parametros) VALUES (:i, 'x', CAST(:m AS jsonb),
                        CAST(:p AS jsonb))"""), {"i": ips, "m": json.dumps(m), "p": json.dumps({"mejor_referencia": "b_media_4s"})})


def test_compuerta_deja_pasar_un_modelo_mejor(base_cargada):
    with base_cargada.begin() as con:
        con.exec_driver_sql("DELETE FROM vd.model_run")
        _modelo(con, 0.25, 0.30)
    assert tareas.compuerta_del_modelo()["ips_donde_gana"] == 1


def test_compuerta_frena_un_modelo_peor(base_cargada):
    with base_cargada.begin() as con:
        con.exec_driver_sql("DELETE FROM vd.model_run")
        _modelo(con, 0.40, 0.30)
    with pytest.raises(tareas.ControlFallido, match="supera"):
        tareas.compuerta_del_modelo()


def test_compuerta_sin_modelos_falla(base_cargada):
    with base_cargada.begin() as con:
        con.exec_driver_sql("DELETE FROM vd.model_run")
    with pytest.raises(tareas.ControlFallido):
        tareas.compuerta_del_modelo()


def test_verificar_fuente_detecta_que_la_fuente_encogio(base_cargada, monkeypatch):
    class Falso:
        def get(self, ds, params=None):
            return [{"n": "5", "ultimo": "2021-05-04T07:40:00"}]
    monkeypatch.setattr(extract, "SocrataClient", lambda *a, **k: Falso())
    with pytest.raises(tareas.ControlFallido, match="fuente"):
        tareas.verificar_fuente()          # la ultima lectura completa trajo 10 filas y ahora hay 5


def test_verificar_fuente_acepta_una_fuente_igual_o_mayor(base_cargada, monkeypatch):
    class Falso:
        def get(self, ds, params=None):
            return [{"n": "12", "ultimo": "2021-05-04T07:40:00"}]
    monkeypatch.setattr(extract, "SocrataClient", lambda *a, **k: Falso())
    assert tareas.verificar_fuente()["filas_fuente"] == 12


def test_flujo_clima_con_cliente_simulado(base_cargada):
    class Falso:
        def get(self, ds, params=None):
            if params and "$select" in params:
                if "sum(" in params["$select"]:
                    return [{"dia": "2021-05-03T00:00:00", "lluvia_mm": "3.5", "n": "144"}]
                return [{"dia": "2021-05-03T00:00:00", "temp_media": "14", "temp_max": "17", "temp_min": "10", "n": "5"}]
            return [{"nombreestacion": "ESTACION FALSA ", "latitud": "1.2", "longitud": "-77.2"}]
    r = pipeline.flujo_clima(base_cargada, cliente=Falso(), desde="2021-05-01", hasta="2021-05-31")
    assert r["dias"] == 1
    with base_cargada.connect() as con:
        assert con.execute(text("SELECT nombre FROM vd.dim_estacion WHERE estacion_id = '0052045080'")).scalar() == "ESTACION FALSA"


def test_exportar_snapshot_con_los_datos_reales(tmp_path):
    from vitaldata import export
    eng = load.get_engine()           # base real (monkeypatch no activo aqui)
    with eng.connect() as con:
        if con.execute(text("SELECT count(*) FROM vd.model_run")).scalar() == 0:
            pytest.skip("Faltan modelos publicados")
    r = export.snapshot(eng, tmp_path)
    texto = (tmp_path / "snapshot.js").read_text(encoding="utf-8")
    assert texto.startswith("window.SNAPSHOT=") and texto.rstrip().endswith(";")
    snap = json.loads(texto[len("window.SNAPSHOT="):].rstrip(";"))
    assert {"ips", "resumen", "metricas", "calidad", "espera_tipica"} <= set(snap)
    assert r["dias_de_pronostico"] > 100


def test_una_carga_incremental_sin_filas_nuevas_no_rompe_la_conciliacion(base_cargada):
    """Una corrida incremental vuelve a traer filas que ya estaban (traslape de 7 dias) y no carga ninguna: la cuenta debe seguir cuadrando."""
    from vitaldata.api import service
    antes = service.calidad(base_cargada)["conciliacion"]
    assert antes["coincide"] is True
    with base_cargada.begin() as con:
        con.execute(text("""INSERT INTO vd.etl_run (flujo, estado, fin, filas_extraidas, filas_duplicadas, filas_rechazadas, filas_cargadas, detalle)
                            VALUES ('triage_urgencias', 'ok', now(), 7, 0, 0, 0, CAST('{"incremental": true}' AS jsonb))"""))
    despues = service.calidad(base_cargada)["conciliacion"]
    assert despues["coincide"] is True and despues["extraidas"] == antes["extraidas"]
