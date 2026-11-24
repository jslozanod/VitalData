import httpx
import pytest

from vitaldata.etl import extract


def cliente_con(handler, **kw):
    return extract.SocrataClient(base="https://x.test/resource", token=kw.pop("token", None), backoff=0.0, max_retries=3,
                                 client=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


def test_reintenta_y_se_recupera(monkeypatch):
    llamadas = {"n": 0}

    def h(req):
        llamadas["n"] += 1
        return httpx.Response(503) if llamadas["n"] < 3 else httpx.Response(200, json=[{"a": 1}])
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)
    assert cliente_con(h).get("abc", {}) == [{"a": 1}] and llamadas["n"] == 3


def test_falla_despues_de_los_reintentos(monkeypatch):
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)
    with pytest.raises(extract.ExtractError):
        cliente_con(lambda r: httpx.Response(500)).get("abc", {})


def test_error_de_cliente_no_se_reintenta():
    n = {"v": 0}

    def h(req):
        n["v"] += 1
        return httpx.Response(404, text="no existe")
    with pytest.raises(extract.ExtractError):
        cliente_con(h).get("abc", {})
    assert n["v"] == 1


def test_el_token_viaja_en_la_cabecera_y_no_en_la_url():
    visto = {}

    def h(req):
        visto["h"], visto["u"] = req.headers.get("x-app-token"), str(req.url)
        return httpx.Response(200, json=[])
    cliente_con(h, token="secreto").get("abc", {"$limit": 1})
    assert visto["h"] == "secreto" and "secreto" not in visto["u"]


def test_respuesta_que_no_es_lista():
    with pytest.raises(extract.ExtractError):
        cliente_con(lambda r: httpx.Response(200, json={"error": True})).get("abc", {})


def test_paginacion_se_detiene_en_la_ultima_pagina():
    def h(req):
        off = int(req.url.params["$offset"])
        return httpx.Response(200, json=[{"i": off + k} for k in range(3 if off < 6 else 1)])
    filas = [f for p in cliente_con(h).paginas("abc", page_size=3) for f in p]
    assert [f["i"] for f in filas] == list(range(7))
