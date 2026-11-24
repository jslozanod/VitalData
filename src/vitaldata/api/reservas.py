"""Reserva de citas y resenas de los pacientes.

Las agendas son del propio VitalData (cada centro tiene franjas de 30 minutos y un numero de cupos por franja). En un piloto
real se conectarian con la agenda del hospital; la logica de cupos, validacion y cancelacion es la misma.
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
import secrets

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from vitaldata.api import service
from vitaldata.models import espera_real

CUPOS_POR_FRANJA = 2
VENTANA_DIAS = 90
ANTICIPACION_MIN = 30
HORAS = [f"{h:02d}:{m:02d}" for h in range(7, 19) for m in (0, 30)]       # 07:00 a 18:30
ESPECIALIDADES = ["Medicina general", "Cita prioritaria", "Pediatría", "Ginecología y obstetricia", "Odontología", "Ortopedia",
                  "Dermatología", "Psicología", "Medicina interna", "Oftalmología", "Otorrinolaringología", "Nutrición",
                  "Cardiología", "Neurología", "Urología"]
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"                              # sin 0, O, 1, I


class Conflicto(Exception):
    """El cupo ya no esta disponible."""


class Invalido(ValueError):
    """Los datos no cumplen las reglas de la reserva."""


def ahora() -> dt.datetime:
    """Hora local de Colombia (UTC-5, sin horario de verano)."""
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).replace(tzinfo=None)


def franja_del_dia(hhmm: str) -> str:
    h = int(hhmm[:2])
    return "madrugada" if h < 6 else "mañana" if h < 12 else "tarde" if h < 18 else "noche"


def _ocupados(engine, ips_id: int, desde: dt.date, hasta: dt.date) -> dict:
    with engine.connect() as con:
        rows = con.execute(text("""SELECT fecha, to_char(hora, 'HH24:MI') AS h, count(*) AS n FROM vd.cita
                                   WHERE ips_id = :i AND fecha BETWEEN :d AND :h AND estado = 'reservada' GROUP BY fecha, hora"""),
                           {"i": ips_id, "d": desde, "h": hasta}).all()
    return {(r.fecha, r.h): int(r.n) for r in rows}


def _es_pasada(fecha: dt.date, hhmm: str, ref: dt.datetime) -> bool:
    return dt.datetime.combine(fecha, dt.time.fromisoformat(hhmm)) < ref + dt.timedelta(minutes=ANTICIPACION_MIN)


def franjas(engine, ips: str, fecha: dt.date) -> dict:
    ips_id = service._ips_id(engine, ips)
    ref = ahora()
    ocup = _ocupados(engine, ips_id, fecha, fecha)
    curva = {}
    for c in espera_real.espera_tipica_por_dia(engine, fecha.weekday()):
        if c["ips"] == ips.upper():
            curva = {h["hora"]: h["espera_min"] for h in c["horas"]}
    fuera = fecha < ref.date() or fecha > ref.date() + dt.timedelta(days=VENTANA_DIAS)
    out = []
    for hhmm in HORAS:
        libres = max(0, CUPOS_POR_FRANJA - ocup.get((fecha, hhmm), 0))
        pasada = fuera or _es_pasada(fecha, hhmm, ref)
        out.append({"hora": hhmm, "franja": franja_del_dia(hhmm), "cupos": CUPOS_POR_FRANJA, "libres": 0 if pasada else libres,
                    "disponible": (not pasada) and libres > 0, "espera_min": curva.get(int(hhmm[:2])), "recomendada": False})
    candidatas = sorted([f for f in out if f["disponible"] and f["espera_min"] is not None], key=lambda f: f["espera_min"])
    for f in candidatas[:3]:
        f["recomendada"] = True
    return {"ips": ips.upper(), "fecha": fecha.isoformat(), "franjas": out}


def calendario(engine, ips: str, mes: str) -> dict:
    try:
        anio, m = (int(x) for x in mes.split("-"))
        primero = dt.date(anio, m, 1)
    except (ValueError, TypeError):
        raise Invalido("El mes debe tener el formato AAAA-MM")
    ips_id = service._ips_id(engine, ips)
    ref = ahora()
    ultimo = dt.date(anio, m, calendar.monthrange(anio, m)[1])
    ocup = _ocupados(engine, ips_id, primero, ultimo)
    espera_dia = {}
    for wd in range(7):
        for c in espera_real.espera_tipica_por_dia(engine, wd):
            if c["ips"] == ips.upper():
                vals = [h["espera_min"] for h in c["horas"] if 7 <= h["hora"] <= 18 and h["espera_min"] is not None]
                espera_dia[wd] = round(sum(vals) / len(vals), 1) if vals else None
    total = len(HORAS) * CUPOS_POR_FRANJA
    dias = []
    for n in range(1, ultimo.day + 1):
        f = dt.date(anio, m, n)
        fuera = f < ref.date() or f > ref.date() + dt.timedelta(days=VENTANA_DIAS)
        libres = 0 if fuera else sum(max(0, CUPOS_POR_FRANJA - ocup.get((f, h), 0)) for h in HORAS if not _es_pasada(f, h, ref))
        nivel = "sin" if libres == 0 else "alta" if libres > total * 0.5 else "media" if libres > total * 0.2 else "baja"
        dias.append({"fecha": f.isoformat(), "dia_semana": f.weekday(), "disponible": libres > 0, "libres": libres, "nivel": nivel,
                     "espera_tipica_min": espera_dia.get(f.weekday())})
    return {"ips": ips.upper(), "mes": mes, "primer_dia_semana": primero.weekday(), "dias": dias}


_CONTACTO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validar_contacto(c: str) -> str:
    c = c.strip()
    if _CONTACTO.match(c):
        return c.lower()
    digitos = re.sub(r"[\s\-()+]", "", c)
    if digitos.isdigit() and 7 <= len(digitos) <= 15:
        return digitos
    raise Invalido("Escribe un correo o un número de celular válido")


def _codigo() -> str:
    return "VD-" + "".join(secrets.choice(ALFABETO) for _ in range(6))


def reservar(engine, req) -> dict:
    ips_id = service._ips_id(engine, req.ips)
    ref = ahora()
    if req.fecha < ref.date() or req.fecha > ref.date() + dt.timedelta(days=VENTANA_DIAS):
        raise Invalido(f"Solo se puede reservar entre hoy y los próximos {VENTANA_DIAS} días")
    if req.hora not in HORAS:
        raise Invalido("Esa hora no está en la agenda (de 7:00 a 18:30, cada 30 minutos)")
    if _es_pasada(req.fecha, req.hora, ref):
        raise Invalido(f"Esa hora ya pasó o es muy pronto: reserva con al menos {ANTICIPACION_MIN} minutos de anticipación")
    if req.especialidad not in ESPECIALIDADES:
        raise Invalido("Elige una especialidad de la lista")
    contacto = _validar_contacto(req.contacto)
    for cupo in range(1, CUPOS_POR_FRANJA + 1):
        codigo = _codigo()
        try:
            with engine.begin() as con:
                con.execute(text("""INSERT INTO vd.cita (codigo, ips_id, fecha, hora, cupo, especialidad, motivo, nombre, contacto)
                                    VALUES (:c, :i, :f, :h, :cu, :e, :m, :n, :ct)"""),
                            {"c": codigo, "i": ips_id, "f": req.fecha, "h": req.hora, "cu": cupo, "e": req.especialidad,
                             "m": (req.motivo or None), "n": req.nombre.strip(), "ct": contacto})
            return {"codigo": codigo, "ips": req.ips.upper(), "fecha": req.fecha.isoformat(), "hora": req.hora, "especialidad": req.especialidad,
                    "estado": "reservada", "mensaje": "Tu cita quedó reservada. Guarda el código para consultarla o cancelarla."}
        except IntegrityError:
            continue                                         # cupo ocupado (o codigo repetido): prueba el siguiente
    raise Conflicto("Ese horario se acaba de llenar. Elige otro.")


def _enmascarar(c: str) -> str:
    return (c[:3] + "***" + c[c.index("@"):]) if "@" in c else ("*" * max(0, len(c) - 3) + c[-3:])


def _cita(engine, codigo: str):
    with engine.connect() as con:
        r = con.execute(text("""SELECT c.codigo, i.nombre AS ips, c.fecha, to_char(c.hora, 'HH24:MI') AS hora, c.especialidad, c.motivo, c.nombre,
                                c.contacto, c.estado FROM vd.cita c JOIN vd.dim_ips i USING (ips_id) WHERE c.codigo = :c"""),
                        {"c": codigo.strip().upper()}).first()
    if r is None:
        raise service.NoEncontrado("No encontramos una cita con ese código")
    return r


def consultar(engine, codigo: str) -> dict:
    r = _cita(engine, codigo)
    return {"codigo": r.codigo, "ips": r.ips, "fecha": r.fecha.isoformat(), "hora": r.hora, "especialidad": r.especialidad, "estado": r.estado,
            "nombre": r.nombre.split()[0], "contacto": _enmascarar(r.contacto)}


def cancelar(engine, codigo: str) -> dict:
    r = _cita(engine, codigo)
    if r.estado == "cancelada":
        return consultar(engine, codigo)
    if _es_pasada(r.fecha, r.hora, ahora()):
        raise Invalido("Esa cita ya pasó y no se puede cancelar")
    with engine.begin() as con:
        con.execute(text("UPDATE vd.cita SET estado = 'cancelada' WHERE codigo = :c"), {"c": r.codigo})
    return consultar(engine, codigo)


# ---------------------------------------------------------------------------------------------------- resenas
def resenas(engine, limite: int = 20) -> dict:
    with engine.connect() as con:
        agg = con.execute(text("""SELECT count(*) AS n, avg(estrellas) AS m, count(*) FILTER (WHERE estrellas = 1) AS e1, count(*) FILTER (WHERE estrellas = 2) AS e2,
                                  count(*) FILTER (WHERE estrellas = 3) AS e3, count(*) FILTER (WHERE estrellas = 4) AS e4, count(*) FILTER (WHERE estrellas = 5) AS e5
                                  FROM vd.resena WHERE visible""")).first()
        filas = con.execute(text("""SELECT estrellas, nombre, comentario, creada FROM vd.resena WHERE visible ORDER BY creada DESC LIMIT :l"""), {"l": limite}).all()
    return {"total": int(agg.n), "promedio": round(float(agg.m), 2) if agg.n else None,
            "distribucion": {str(i): int(getattr(agg, f"e{i}")) for i in range(1, 6)},
            "resenas": [{"estrellas": r.estrellas, "nombre": r.nombre or "Anónimo", "comentario": r.comentario, "fecha": r.creada.date().isoformat()} for r in filas]}


def crear_resena(engine, req) -> dict:
    comentario = re.sub(r"\s+", " ", req.comentario).strip()
    with engine.begin() as con:
        dup = con.execute(text("SELECT 1 FROM vd.resena WHERE comentario = :c AND creada > now() - interval '1 day'"), {"c": comentario}).first()
        if dup:
            raise Conflicto("Ya recibimos esa opinión. ¡Gracias!")
        con.execute(text("INSERT INTO vd.resena (estrellas, nombre, comentario) VALUES (:e, :n, :c)"),
                    {"e": req.estrellas, "n": (req.nombre or "").strip() or None, "c": comentario})
    return {"mensaje": "¡Gracias por tu opinión!"}


# ---------------------------------------------------------------------------------------------------- hospitales
def solicitar_demo(engine, req) -> dict:
    contacto = _validar_contacto(req.contacto)
    with engine.begin() as con:
        dup = con.execute(text("SELECT 1 FROM vd.solicitud_demo WHERE contacto = :c AND creada > now() - interval '1 hour'"), {"c": contacto}).first()
        if dup:
            raise Conflicto("Ya recibimos tu solicitud. Te contactaremos pronto.")
        con.execute(text("""INSERT INTO vd.solicitud_demo (institucion, nombre, cargo, contacto, mensaje) VALUES (:i, :n, :c, :ct, :m)"""),
                    {"i": req.institucion.strip(), "n": req.nombre.strip(), "c": (req.cargo or "").strip() or None, "ct": contacto, "m": (req.mensaje or "").strip() or None})
    return {"mensaje": "Recibimos tu solicitud. Nuestro equipo te contactará para coordinar la demostración."}
