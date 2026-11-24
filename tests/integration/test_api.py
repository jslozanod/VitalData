"""Pruebas de la API contra la base con los datos reales cargados y los modelos publicados.
Se ejecutan despues de: correr_etl.py --init/--triage/--clima y publicar_modelos.py."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from vitaldata.api.main import app, get_engine

pytestmark = pytest.mark.integration
IPS = "CENTRO HOSPITAL LA ROSA"


@pytest.fixture(scope="module")
def client():
    try:
        with get_engine().connect() as con:
            con.execute(text("SELECT 1"))
            if con.execute(text("SELECT count(*) FROM vd.model_run")).scalar() == 0:
                pytest.skip("Faltan modelos publicados (python scripts/publicar_modelos.py)")
    except OperationalError:
        pytest.skip("PostgreSQL no esta disponible")
    return TestClient(app)


@pytest.fixture(scope="module")
def fecha_valida(client):
    r = client.get("/api/ips").json()
    ips = next(i for i in r if i["nombre"] == IPS)
    return ips["rango_pronostico"]["desde"]


def test_health(client):
    assert client.get("/api/health").json()["estado"] == "ok"


def test_resumen_coincide_con_la_base(client):
    r = client.get("/api/resumen").json()
    with get_engine().connect() as con:
        n = con.execute(text("SELECT count(*) FROM vd.fact_atencion")).scalar()
    assert r["atenciones"] == n and r["ips"] >= 3


def test_lista_de_ips(client):
    r = client.get("/api/ips").json()
    nombres = {i["nombre"] for i in r}
    assert IPS in nombres
    assert all("atenciones" in i for i in r)


def test_pronostico_tiene_24_horas_y_real(client, fecha_valida):
    r = client.get("/api/pronostico", params={"ips": IPS, "fecha": fecha_valida}).json()
    assert len(r["horas"]) == 24
    assert all(h["pronostico"] is not None and h["lo80"] <= h["pronostico"] + 1e-6 <= h["hi80"] + 1 for h in r["horas"])
    assert r["total_real"] >= 0


def test_pronostico_fuera_de_rango_es_404(client):
    r = client.get("/api/pronostico", params={"ips": IPS, "fecha": "2019-01-01"})
    assert r.status_code == 404 and "Fechas disponibles" in r.json()["detalle"]


def test_ips_inexistente_es_404(client):
    assert client.get("/api/pronostico", params={"ips": "NO EXISTE", "fecha": "2022-08-10"}).status_code == 404


@pytest.mark.parametrize("params", [{"dotacion": 0}, {"dotacion": 100}, {"meta_min": 0}, {"servicio_min": 1}, {"fecha": "no-es-fecha"}])
def test_personal_rechaza_parametros_fuera_de_limite(client, fecha_valida, params):
    base = {"ips": IPS, "fecha": fecha_valida, "dotacion": 3, "meta_min": 15, "servicio_min": 30}
    assert client.get("/api/personal", params={**base, **params}).status_code == 422


def test_mas_dotacion_no_aumenta_la_espera(client, fecha_valida):
    def espera(dot):
        r = client.get("/api/personal", params={"ips": IPS, "fecha": fecha_valida, "dotacion": dot}).json()
        return sum((999 if h["saturada"] else h["espera_con_dotacion_min"]) for h in r["horas"])
    assert espera(6) <= espera(3) <= espera(2)


def test_personal_necesario_es_consistente_con_la_meta(client, fecha_valida):
    r = client.get("/api/personal", params={"ips": IPS, "fecha": fecha_valida, "meta_min": 10}).json()
    r2 = client.get("/api/personal", params={"ips": IPS, "fecha": fecha_valida, "meta_min": 40}).json()
    assert r["pico_personal"] >= r2["pico_personal"]


def test_escenario_mas_demanda_sube_el_total(client, fecha_valida):
    base = {"ips": IPS, "fecha": fecha_valida}
    a = client.post("/api/escenario", json={**base, "factor_nivel": 1.0}).json()
    b = client.post("/api/escenario", json={**base, "factor_nivel": 1.5}).json()
    assert b["total_escenario"] > a["total_escenario"] and a["cambio_pct"] == 0.0


@pytest.mark.parametrize("cuerpo", [{"factor_nivel": 5}, {"lluvia_mm": -1}, {"temp_media": 80}, {"ips": "x"}])
def test_escenario_valida_limites(client, fecha_valida, cuerpo):
    assert client.post("/api/escenario", json={"ips": IPS, "fecha": fecha_valida, **cuerpo}).status_code == 422


def test_metricas_incluyen_referencias(client):
    r = client.get("/api/metricas", params={"ips": IPS}).json()
    assert len(r) == 1 and "b_media_4s" in r[0]["metricas"]["metricas"]["3h"]


def test_calidad_concilia(client):
    r = client.get("/api/calidad").json()
    assert r["conciliacion"]["coincide"] is True


def test_espera_real_tiene_curva_y_correlacion(client):
    r = client.get("/api/espera-real", params={"ips": IPS}).json()
    assert len(r["curva"]) >= 4 and r["correlacion"]["spearman"] is not None


def test_orientar_alarma_y_leve(client):
    a = client.post("/api/orientar", json={"texto": "me duele el pecho y me cuesta respirar", "hora": 10}).json()
    assert a["accion"] == "urgencias_ya" and a["ranking"] == []
    b = client.post("/api/orientar", json={"texto": "tengo gripa", "hora": 10}).json()
    assert b["accion"] == "orientacion_leve" and len(b["ranking"]) >= 3
    esperas = [r["espera_esperada_min"] for r in b["ranking"]]
    assert esperas == sorted(esperas)


@pytest.mark.parametrize("cuerpo", [{"texto": "", "hora": 10}, {"texto": "gripa", "hora": 25}, {"texto": "x" * 500, "hora": 5}])
def test_orientar_valida_entrada(client, cuerpo):
    assert client.post("/api/orientar", json=cuerpo).status_code == 422


def test_usabilidad_guarda_y_resume(client):
    cuerpo = {"rol": "otro", "tareas_ok": 4, "tareas_total": 5, "segundos": 300, "sus": [4, 2, 4, 2, 4, 2, 4, 2, 4, 2],
              "comentario": "prueba automatica"}
    r = client.post("/api/usabilidad", json=cuerpo)
    assert r.status_code == 201 and r.json()["sus_puntaje"] == 75.0
    sid = r.json()["sesion_id"]
    assert client.get("/api/usabilidad/resumen").json()["sesiones"] >= 1
    with get_engine().begin() as con:       # no se deja basura de prueba en los resultados reales
        con.execute(text("DELETE FROM vd.usabilidad_sesion WHERE sesion_id = :s"), {"s": uuid.UUID(sid)})


@pytest.mark.parametrize("cambio", [{"sus": [3] * 9}, {"sus": [6] * 10}, {"tareas_ok": 9}, {"rol": "alien"}, {"segundos": -1}])
def test_usabilidad_rechaza_datos_invalidos(client, cambio):
    cuerpo = {"rol": "otro", "tareas_ok": 4, "tareas_total": 5, "segundos": 300, "sus": [3] * 10, **cambio}
    assert client.post("/api/usabilidad", json=cuerpo).status_code == 422


def test_serie_por_dia_sin_fechas(client):
    r = client.get("/api/serie", params={"ips": IPS, "nivel": "dia"})
    assert r.status_code == 200 and len(r.json()) > 300


def test_serie_por_hora_en_un_rango(client):
    r = client.get("/api/serie", params={"ips": IPS, "nivel": "hora", "desde": "2022-08-10", "hasta": "2022-08-11"}).json()
    assert 0 < len(r) <= 24 and all(x["t"].startswith("2022-08-10") for x in r)


@pytest.mark.parametrize("params", [{"nivel": "semana"}, {"desde": "2022-09-01", "hasta": "2022-08-01"}])
def test_serie_valida_parametros(client, params):
    assert client.get("/api/serie", params={"ips": IPS, **params}).status_code == 422


def test_perfil_horario_tiene_24_horas_por_tipo_de_dia(client):
    r = client.get("/api/perfil", params={"ips": IPS}).json()
    assert set(r) == {"laboral", "sabado", "domingo"} and all(len(v) == 24 for v in r.values())
    assert max(r["laboral"]) > min(r["laboral"])


def test_corridas_y_resumen_de_usabilidad(client):
    assert len(client.get("/api/etl/corridas", params={"limite": 5}).json()) <= 5
    assert client.get("/api/etl/corridas", params={"limite": 500}).status_code == 422
    assert "sesiones" in client.get("/api/usabilidad/resumen").json()


def test_espera_tipica_por_dia_tiene_24_horas_por_centro(client):
    r = client.get("/api/espera-tipica", params={"dia_semana": 5}).json()
    assert r["dia_semana"] == 5 and len(r["centros"]) >= 3
    assert all(len(c["horas"]) == 24 for c in r["centros"])
    assert any(h["espera_min"] is not None for c in r["centros"] for h in c["horas"])


@pytest.mark.parametrize("dia", [-1, 7])
def test_espera_tipica_rechaza_dias_fuera_de_rango(client, dia):
    assert client.get("/api/espera-tipica", params={"dia_semana": dia}).status_code == 422


def test_orientar_con_dia_exacto_coincide_con_la_curva_del_dia(client):
    curva = client.get("/api/espera-tipica", params={"dia_semana": 2}).json()["centros"]
    esperado = {c["ips"]: c["horas"][10]["espera_min"] for c in curva if c["horas"][10]["espera_min"] is not None}
    r = client.post("/api/orientar", json={"texto": "tengo gripa", "hora": 10, "dia_semana": 2}).json()
    assert {x["ips"]: x["espera_esperada_min"] for x in r["ranking"]} == esperado


def test_orientar_rechaza_dia_de_la_semana_invalido(client):
    assert client.post("/api/orientar", json={"texto": "gripa", "hora": 10, "dia_semana": 9}).status_code == 422
