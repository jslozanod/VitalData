"""Reservas de citas y resenas contra PostgreSQL. Cada prueba borra lo que crea para no dejar basura en los datos reales."""
import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from vitaldata.api import reservas
from vitaldata.api.main import app, get_engine

pytestmark = pytest.mark.integration
IPS = "CENTRO HOSPITAL LA ROSA"


@pytest.fixture(scope="module")
def client():
    try:
        with get_engine().connect() as con:
            con.execute(text("SELECT 1 FROM vd.cita LIMIT 1"))
    except OperationalError:
        pytest.skip("PostgreSQL no esta disponible")
    except Exception:
        pytest.skip("Faltan las tablas de citas (python scripts/correr_etl.py --init)")
    return TestClient(app)


@pytest.fixture()
def limpiar():
    creados = []
    yield creados
    with get_engine().begin() as con:
        for c in creados:
            con.execute(text("DELETE FROM vd.cita WHERE codigo = :c"), {"c": c})


def _fecha(dias=10):
    return (reservas.ahora().date() + dt.timedelta(days=dias)).isoformat()


def _cuerpo(**cambios):
    base = {"ips": IPS, "fecha": _fecha(), "hora": "10:00", "especialidad": "Medicina general", "motivo": "Control",
            "nombre": "Prueba Automatica", "contacto": "prueba@example.com", "acepta_datos": True}
    return {**base, **cambios}


def test_especialidades_y_horas(client):
    r = client.get("/api/citas/especialidades").json()
    assert "Medicina general" in r["especialidades"] and r["horas"][0] == "07:00" and r["horas"][-1] == "18:30"


def test_calendario_del_mes_marca_dias_pasados_y_futuros(client):
    hoy = reservas.ahora().date()
    r = client.get("/api/citas/calendario", params={"ips": IPS, "mes": hoy.strftime("%Y-%m")}).json()
    assert len(r["dias"]) >= 28 and r["primer_dia_semana"] == hoy.replace(day=1).weekday()
    por = {d["fecha"]: d for d in r["dias"]}
    if hoy.day > 1:
        assert por[hoy.replace(day=1).isoformat()]["disponible"] is False          # un dia pasado no se puede reservar
    futuro = client.get("/api/citas/calendario", params={"ips": IPS, "mes": (hoy + dt.timedelta(days=40)).strftime("%Y-%m")}).json()
    assert any(d["disponible"] for d in futuro["dias"]) and all(d["espera_tipica_min"] is not None for d in futuro["dias"])


def test_calendario_rechaza_mes_mal_escrito(client):
    assert client.get("/api/citas/calendario", params={"ips": IPS, "mes": "mayo"}).status_code == 422


def test_franjas_traen_espera_y_recomendadas(client):
    r = client.get("/api/citas/franjas", params={"ips": IPS, "fecha": _fecha()}).json()
    assert len(r["franjas"]) == 24
    rec = [f for f in r["franjas"] if f["recomendada"]]
    assert 1 <= len(rec) <= 3 and all(f["disponible"] and f["espera_min"] is not None for f in rec)
    assert {f["franja"] for f in r["franjas"]} == {"mañana", "tarde", "noche"}


def test_reservar_consultar_y_cancelar(client, limpiar):
    r = client.post("/api/citas", json=_cuerpo())
    assert r.status_code == 201
    cod = r.json()["codigo"]; limpiar.append(cod)
    assert cod.startswith("VD-") and len(cod) == 9
    c = client.get(f"/api/citas/{cod.lower()}").json()                  # el codigo no distingue mayusculas
    assert c["estado"] == "reservada" and c["nombre"] == "Prueba" and "@" in c["contacto"] and "prueba@" not in c["contacto"]
    x = client.post(f"/api/citas/{cod}/cancelar").json()
    assert x["estado"] == "cancelada"
    assert client.post(f"/api/citas/{cod}/cancelar").json()["estado"] == "cancelada"      # cancelar dos veces no falla


def test_una_franja_se_llena_y_al_cancelar_se_libera(client, limpiar):
    cuerpo = _cuerpo(fecha=_fecha(12), hora="11:30")
    codigos = []
    for _ in range(reservas.CUPOS_POR_FRANJA):
        r = client.post("/api/citas", json=cuerpo)
        assert r.status_code == 201
        codigos.append(r.json()["codigo"]); limpiar.append(codigos[-1])
    lleno = client.post("/api/citas", json=cuerpo)
    assert lleno.status_code == 409 and "horario" in lleno.json()["detalle"]
    franja = next(f for f in client.get("/api/citas/franjas", params={"ips": IPS, "fecha": cuerpo["fecha"]}).json()["franjas"] if f["hora"] == "11:30")
    assert franja["libres"] == 0 and franja["disponible"] is False
    client.post(f"/api/citas/{codigos[0]}/cancelar")
    otra = client.post("/api/citas", json=cuerpo)
    assert otra.status_code == 201
    limpiar.append(otra.json()["codigo"])


@pytest.mark.parametrize("cambio,texto", [
    ({"fecha": "2020-01-01"}, "entre hoy"),
    ({"fecha": (reservas.ahora().date() + dt.timedelta(days=400)).isoformat()}, "entre hoy"),
    ({"hora": "03:00"}, "agenda"),
    ({"hora": "10:15"}, "agenda"),
    ({"especialidad": "Cirugía plástica"}, "especialidad"),
    ({"contacto": "no es un contacto"}, "correo"),
])
def test_reservar_rechaza_datos_invalidos(client, cambio, texto):
    r = client.post("/api/citas", json=_cuerpo(**cambio))
    assert r.status_code == 422 and texto in r.json()["detalle"].lower()


@pytest.mark.parametrize("cambio", [{"acepta_datos": False}, {"nombre": "A"}, {"hora": "mañana"}, {"ips": ""}])
def test_reservar_exige_consentimiento_y_campos_validos(client, cambio):
    assert client.post("/api/citas", json=_cuerpo(**cambio)).status_code == 422


def test_ips_inexistente_y_codigo_inexistente(client):
    assert client.post("/api/citas", json=_cuerpo(ips="NO EXISTE")).status_code == 404
    assert client.get("/api/citas/VD-NOEXIS").status_code == 404


def test_hoy_no_deja_reservar_horas_que_ya_pasaron(client):
    ref = reservas.ahora()
    pasada = (ref - dt.timedelta(hours=2)).strftime("%H:00")
    if "07:00" <= pasada <= "18:30":
        r = client.post("/api/citas", json=_cuerpo(fecha=ref.date().isoformat(), hora=pasada))
        assert r.status_code == 422


# ---------------------------------------------------------------- resenas
def test_resenas_se_guardan_y_cuentan_en_el_promedio(client):
    marca = f"Prueba automatica {uuid.uuid4().hex[:8]}"
    try:
        antes = client.get("/api/resenas").json()
        r = client.post("/api/resenas", json={"estrellas": 4, "nombre": "Tester", "comentario": marca})
        assert r.status_code == 201
        despues = client.get("/api/resenas").json()
        assert despues["total"] == antes["total"] + 1 and despues["resenas"][0]["comentario"] == marca
        assert despues["distribucion"]["4"] == antes["distribucion"]["4"] + 1
        assert client.post("/api/resenas", json={"estrellas": 4, "comentario": marca}).status_code == 409       # duplicada
    finally:
        with get_engine().begin() as con:
            con.execute(text("DELETE FROM vd.resena WHERE comentario = :c"), {"c": marca})


@pytest.mark.parametrize("cuerpo", [{"estrellas": 0, "comentario": "muy bueno todo"}, {"estrellas": 6, "comentario": "muy bueno todo"},
                                    {"estrellas": 5, "comentario": "ok"}, {"estrellas": 5, "comentario": "x" * 501}])
def test_resenas_validan_limites(client, cuerpo):
    assert client.post("/api/resenas", json=cuerpo).status_code == 422


# ---------------------------------------------------------------- solicitudes de hospitales
def test_un_hospital_puede_pedir_una_demostracion(client):
    marca = f"Hospital de prueba {uuid.uuid4().hex[:6]}"
    cuerpo = {"institucion": marca, "nombre": "Tester", "cargo": "Coordinador", "contacto": f"{uuid.uuid4().hex[:8]}@example.com", "mensaje": "Quiero ver el panel", "acepta_datos": True}
    try:
        assert client.post("/api/hospitales/contacto", json=cuerpo).status_code == 201
        assert client.post("/api/hospitales/contacto", json=cuerpo).status_code == 409          # la misma persona no se duplica
    finally:
        with get_engine().begin() as con:
            con.execute(text("DELETE FROM vd.solicitud_demo WHERE institucion = :i"), {"i": marca})


@pytest.mark.parametrize("cambio", [{"acepta_datos": False}, {"contacto": "no es un contacto"}, {"institucion": "A"}, {"nombre": ""}])
def test_solicitud_de_hospital_valida_campos(client, cambio):
    cuerpo = {"institucion": "Hospital X", "nombre": "Persona", "contacto": "persona@example.com", "acepta_datos": True, **cambio}
    assert client.post("/api/hospitales/contacto", json=cuerpo).status_code == 422
