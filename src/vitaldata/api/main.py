"""API de VitalData (FastAPI). Documentacion interactiva en /docs."""
from __future__ import annotations

import datetime as dt
import logging

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from vitaldata import config
from vitaldata.api import reservas, schemas, service
from vitaldata.etl import load

log = logging.getLogger("vitaldata.api")
app = FastAPI(title="VitalData API", version="1.0.0",
              description="Pronostico de llegadas a urgencias y personal recomendado, con datos abiertos de la E.S.E. Pasto Salud y del IDEAM.")

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = load.get_engine()
    return _engine


@app.exception_handler(service.NoEncontrado)
async def no_encontrado(_, exc: service.NoEncontrado):
    return JSONResponse(status_code=404, content={"detalle": str(exc)})


@app.exception_handler(reservas.Conflicto)
async def conflicto(_, exc: reservas.Conflicto):
    return JSONResponse(status_code=409, content={"detalle": str(exc)})


@app.exception_handler(reservas.Invalido)
async def invalido(_, exc: reservas.Invalido):
    return JSONResponse(status_code=422, content={"detalle": str(exc)})


@app.exception_handler(SQLAlchemyError)
async def error_base(_, exc: SQLAlchemyError):
    log.exception("Error de base de datos")
    return JSONResponse(status_code=503, content={"detalle": "La base de datos no responde. Intenta de nuevo en unos segundos."})


@app.get("/api/health", tags=["sistema"])
def health(engine=Depends(get_engine)):
    with engine.connect() as con:
        con.execute(text("SELECT 1"))
    return {"estado": "ok", "hora": dt.datetime.now().isoformat(timespec="seconds")}


@app.get("/api/resumen", tags=["datos"])
def resumen(engine=Depends(get_engine)):
    return service.resumen(engine)


@app.get("/api/ips", tags=["datos"])
def ips(engine=Depends(get_engine)):
    lista = service.listar_ips(engine)
    for i in lista:
        if i["modelable"]:
            try:
                i["rango_pronostico"] = service.rango_fechas_pronostico(engine, i["nombre"])
            except service.NoEncontrado:
                i["rango_pronostico"] = None
    return lista


@app.get("/api/serie", tags=["datos"])
def serie(ips: str = Query(min_length=3, max_length=80), desde: dt.date | None = None, hasta: dt.date | None = None,
          nivel: str = Query("dia", pattern="^(dia|hora)$"), engine=Depends(get_engine)):
    if desde and hasta and desde > hasta:
        raise HTTPException(422, "desde no puede ser posterior a hasta")
    return service.serie(engine, ips, str(desde) if desde else None, str(hasta) if hasta else None, nivel)


@app.get("/api/perfil", tags=["datos"])
def perfil(ips: str = Query(min_length=3, max_length=80), engine=Depends(get_engine)):
    return service.perfil_horario(engine, ips)


@app.get("/api/pronostico", tags=["modelo"])
def pronostico(ips: str = Query(min_length=3, max_length=80), fecha: dt.date = Query(), engine=Depends(get_engine)):
    return service.pronostico_dia(engine, ips, fecha)


@app.get("/api/personal", tags=["modelo"])
def personal(ips: str = Query(min_length=3, max_length=80), fecha: dt.date = Query(),
             servicio_min: float = Query(30, ge=5, le=180), meta_min: float = Query(15, ge=1, le=120),
             dotacion: int = Query(3, ge=1, le=60), engine=Depends(get_engine)):
    return service.personal_dia(engine, ips, fecha, servicio_min, meta_min, dotacion)


@app.post("/api/escenario", tags=["modelo"])
def escenario(req: schemas.EscenarioIn, engine=Depends(get_engine)):
    return service.escenario(engine, req)


@app.get("/api/metricas", tags=["modelo"])
def metricas(ips: str | None = Query(None, max_length=80), engine=Depends(get_engine)):
    return service.metricas(engine, ips)


@app.get("/api/espera-real", tags=["datos"])
def espera_real(ips: str = Query(min_length=3, max_length=80), engine=Depends(get_engine)):
    return service.espera_real_ips(engine, ips)


@app.get("/api/calidad", tags=["datos"])
def calidad(engine=Depends(get_engine)):
    return service.calidad(engine)


@app.get("/api/etl/corridas", tags=["sistema"])
def corridas(limite: int = Query(20, ge=1, le=100), engine=Depends(get_engine)):
    return service.corridas(engine, limite)


@app.get("/api/espera-tipica", tags=["paciente"])
def espera_tipica(dia_semana: int = Query(..., ge=0, le=6, description="0 = lunes ... 6 = domingo"), engine=Depends(get_engine)):
    """Espera media historica por hora de cada centro en ese dia de la semana."""
    return service.espera_por_dia(engine, dia_semana)


@app.post("/api/orientar", tags=["paciente"])
def orientar(req: schemas.OrientarIn, engine=Depends(get_engine)):
    return service.orientar(engine, req)


@app.get("/api/citas/especialidades", tags=["citas"])
def especialidades():
    return {"especialidades": reservas.ESPECIALIDADES, "horas": reservas.HORAS, "cupos_por_franja": reservas.CUPOS_POR_FRANJA}


@app.get("/api/citas/calendario", tags=["citas"])
def citas_calendario(ips: str = Query(..., min_length=2), mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"), engine=Depends(get_engine)):
    """Dias del mes con cupos libres y espera tipica del dia de la semana."""
    return reservas.calendario(engine, ips, mes)


@app.get("/api/citas/franjas", tags=["citas"])
def citas_franjas(ips: str = Query(..., min_length=2), fecha: dt.date = Query(...), engine=Depends(get_engine)):
    """Franjas de 30 minutos de un dia, con cupos libres y la espera tipica; marca las tres mas recomendadas."""
    return reservas.franjas(engine, ips, fecha)


@app.post("/api/citas", status_code=201, tags=["citas"])
def citas_reservar(req: schemas.CitaIn, engine=Depends(get_engine)):
    return reservas.reservar(engine, req)


@app.get("/api/citas/{codigo}", tags=["citas"])
def citas_consultar(codigo: str, engine=Depends(get_engine)):
    return reservas.consultar(engine, codigo)


@app.post("/api/citas/{codigo}/cancelar", tags=["citas"])
def citas_cancelar(codigo: str, engine=Depends(get_engine)):
    return reservas.cancelar(engine, codigo)


@app.post("/api/hospitales/contacto", status_code=201, tags=["hospitales"])
def hospitales_contacto(req: schemas.SolicitudDemoIn, engine=Depends(get_engine)):
    """Un hospital pide una demostracion."""
    return reservas.solicitar_demo(engine, req)


@app.get("/api/resenas", tags=["resenas"])
def resenas_listar(engine=Depends(get_engine)):
    return reservas.resenas(engine)


@app.post("/api/resenas", status_code=201, tags=["resenas"])
def resenas_crear(req: schemas.ResenaIn, engine=Depends(get_engine)):
    return reservas.crear_resena(engine, req)


@app.post("/api/usabilidad", response_model=schemas.UsabilidadOut, status_code=201, tags=["usabilidad"])
def usabilidad(req: schemas.UsabilidadIn, engine=Depends(get_engine)):
    return service.guardar_usabilidad(engine, req)


@app.get("/api/usabilidad/resumen", tags=["usabilidad"])
def usabilidad_resumen(engine=Depends(get_engine)):
    return service.resumen_usabilidad(engine)


# La pagina web se sirve desde la misma API: una sola direccion para todo.
_web = config.ROOT / "web"
if _web.exists():
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
