import pytest

from vitaldata.api import asistente, service


@pytest.mark.parametrize("texto", ["Tengo dolor de pecho desde hace una hora", "me cuesta respirar",
                                   "mi hijo tuvo una convulsión", "se desmayó", "vomitó sangre",
                                   "Me duele el pecho", "siento opresión en el pecho"])
def test_alarma(texto):
    assert asistente.clasificar(texto)["nivel"] == "alarma"


@pytest.mark.parametrize("texto", ["tengo gripa y tos", "un resfriado", "dolor de garganta"])
def test_leve(texto):
    assert asistente.clasificar(texto)["nivel"] == "leve"


def test_alarma_gana_sobre_leve():
    assert asistente.clasificar("tengo gripa pero ahora me cuesta respirar")["nivel"] == "alarma"


def test_texto_vacio_o_muy_corto():
    assert asistente.clasificar("  ")["nivel"] == "sin_informacion"
    assert asistente.clasificar("a")["nivel"] == "sin_informacion"


def test_alarma_no_muestra_ranking():
    r = asistente.respuesta({"nivel": "alarma", "categoria": None}, [{"ips": "X", "espera_esperada_min": 5}], {})
    assert r["accion"] == "urgencias_ya" and r["mostrar_ranking"] is False


def test_sus_casos_extremos():
    assert service.sus_puntaje([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0     # todo lo positivo
    assert service.sus_puntaje([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0.0       # todo lo negativo
    assert service.sus_puntaje([3] * 10) == 50.0


# ---------------------------------------------------------------- orientacion en salud
from vitaldata.api import conocimiento  # noqa: E402

CAMPOS = ("id", "nombre", "nivel", "patrones", "ejemplos", "resumen", "casa", "medicamentos", "consultar_si", "alarma")


def test_cada_condicion_tiene_todos_los_campos_y_listas_con_contenido():
    ids = [c["id"] for c in conocimiento.CONDICIONES]
    assert len(ids) == len(set(ids)) and len(ids) >= 15
    for c in conocimiento.CONDICIONES:
        assert all(k in c for k in CAMPOS), c["id"]
        assert c["nivel"] in ("leve", "consulta_pronto")
        assert all(c[k] for k in ("casa", "medicamentos", "consultar_si", "alarma", "ejemplos")), c["id"]


@pytest.mark.parametrize("cond", conocimiento.CONDICIONES, ids=lambda c: c["id"])
def test_los_ejemplos_de_cada_condicion_la_reconocen(cond):
    for ej in cond["ejemplos"]:
        a = asistente.analizar(ej)
        assert a["intencion"] in ("sintomas", "alarma"), ej
        if a["intencion"] == "sintomas":
            assert cond["id"] in [c["id"] for c in a["condiciones"]], ej


def test_las_recomendaciones_de_medicamentos_no_dan_dosis_ni_antibioticos_ni_formula():
    import re
    for c in conocimiento.CONDICIONES:
        for m in c["medicamentos"]:
            assert not re.search(r"\d+\s?(mg|ml|gotas|tabletas|pastillas|g\b)", m.lower()), m
            assert not re.search(r"\b(amoxicilina|azitromicina|ciprofloxacino|prednisona|tramadol|diazepam)\b", m.lower()), m
    assert "no es una fórmula médica" in conocimiento.AVISO_MEDICAMENTOS.lower() or "no una fórmula" in conocimiento.AVISO_MEDICAMENTOS.lower()


def test_sintoma_comun_devuelve_guia_con_pasos_y_ranking():
    r = asistente.construir(asistente.analizar("tengo fiebre y dolor de garganta"), [{"ips": "A", "espera_esperada_min": 5}], {})
    assert r["accion"] == "orientacion_leve" and r["mostrar_ranking"] is True
    assert r["guia"]["id"] == "fiebre" and r["tambien"] == ["Dolor de garganta"]
    assert r["guia"]["alarma"] and "aviso_medicamentos" in r["guia"]


def test_condiciones_que_requieren_valoracion_piden_cita_pronto():
    r = asistente.construir(asistente.analizar("me torcí el tobillo"), [], {})
    assert r["accion"] == "consulta_pronto"


def test_bebe_con_fiebre_es_urgencia():
    r = asistente.construir(asistente.analizar("mi bebé tiene fiebre"), [{"ips": "A", "espera_esperada_min": 5}], {})
    assert r["accion"] == "urgencias_ya" and r["mostrar_ranking"] is False


def test_advertencias_para_ninos_y_embarazo():
    r = asistente.construir(asistente.analizar("mi hijo tiene tos"), [], {})
    assert "pediatra" in r["mensaje"]
    r = asistente.construir(asistente.analizar("estoy embarazada y tengo dolor de cabeza"), [], {})
    assert "embarazada" in r["mensaje"]


@pytest.mark.parametrize("texto,accion", [("hola", "conversacion"), ("gracias", "conversacion"), ("qué puedes hacer", "conversacion"),
                                          ("quiero pedir una cita", "orientacion_cita"), ("qué me puedo tomar", "conversacion"),
                                          ("asdfgh qwerty", "orientacion_general")])
def test_conversacion_basica(texto, accion):
    assert asistente.construir(asistente.analizar(texto), [{"ips": "A", "espera_esperada_min": 5}], {})["accion"] == accion


def test_senales_de_alarma_nuevas():
    for t in ["se me hinchó la lengua", "tengo labios morados", "me falta el aire", "tuve un golpe fuerte en la cabeza"]:
        assert asistente.analizar(t)["intencion"] == "alarma", t


# ---------------------------------------------------------------- medicamentos, tramites, contexto, dosis y errores de escritura
def test_hay_mas_de_90_temas_de_salud_con_ids_unicos():
    ids = [c["id"] for c in conocimiento.CONDICIONES]
    assert len(ids) >= 90 and len(ids) == len(set(ids))


@pytest.mark.parametrize("m", conocimiento.MEDICAMENTOS, ids=lambda m: m["id"])
def test_cada_medicamento_se_reconoce_y_no_trae_dosis(m):
    import re
    nombre = m["patrones"][0].replace("\b", "")
    a = asistente.analizar(f"para qué sirve {nombre}")
    assert a["intencion"] == "medicamento" and a["medicamentos"][0]["id"] == m["id"]
    for t in [m["para_que"]] + m["precauciones"]:
        assert not re.search(r"\d+\s?(mg|ml|gotas|tabletas|pastillas|cucharadas)", t.lower()), t


def test_pregunta_por_dosis_se_rechaza_con_cuidado():
    r = asistente.construir(asistente.analizar("cuántas pastillas de ibuprofeno me tomo"), [], {})
    assert r["accion"] == "conversacion" and "No puedo indicar dosis" in r["mensaje"] and "farmacéutico" in r["mensaje"]


@pytest.mark.parametrize("texto,id_info", [("qué debo llevar a la cita", "documentos"), ("cuáles son mis derechos", "derechos"), ("quiero hacerme un chequeo", "chequeos"),
                                           ("cómo me preparo para un examen de sangre", "examenes"), ("cuánto cuesta la consulta", "cuanto_cuesta")])
def test_tramites_y_prevencion(texto, id_info):
    a = asistente.analizar(texto)
    assert a["intencion"] == "info" and a["info"]["id"] == id_info
    assert asistente.construir(a, [], {})["ficha"]["items"]


def test_preguntas_de_seguimiento_usan_el_tema_anterior():
    a = asistente.analizar("¿y qué puedo tomar?", contexto="fiebre")
    r = asistente.construir(a, [], {})
    assert a["intencion"] == "contexto" and "Acetaminofén" in " ".join(r["ficha"]["items"]) and r["guia"]["id"] == "fiebre"
    assert asistente.analizar("¿cuándo debo consultar?", contexto="gripa")["intencion"] == "contexto"
    assert asistente.analizar("¿qué puedo tomar?")["intencion"] == "medicina_sin_sintoma"          # sin tema previo, pregunta por el sintoma


@pytest.mark.parametrize("texto,tema", [("dolor de cavesa", "cabeza"), ("tengo fiebe", "fiebre"), ("me duele el estomgo", "estomago"), ("qwerty asdfgh", None)])
def test_tolera_errores_de_escritura(texto, tema):
    a = asistente.analizar(texto)
    if tema:
        assert tema in [c["id"] for c in a["condiciones"]]
    else:
        assert a["intencion"] == "no_entendido"


def test_preguntas_sobre_los_datos_se_marcan_para_responder_con_cifras_reales():
    for t, sub in [("cuál es la hora pico", "pico"), ("qué es el triage", "triage"), ("qué tan preciso es el pronóstico", "precision"), ("de dónde salen los datos", "fuente")]:
        a = asistente.analizar(t)
        assert a["intencion"] == "datos" and a["subtipo"] == sub
