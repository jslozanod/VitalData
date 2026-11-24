"""Logica de negocio de la API. Cada funcion recibe el engine para poder probarla sin levantar el servidor."""
from __future__ import annotations

import math
import uuid
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from vitaldata import config
from vitaldata.api import asistente
from vitaldata.models import cola, data, espera_real
from vitaldata.models.publicar import slug


class NoEncontrado(Exception):
    pass


# ---------------------------------------------------------------- catalogo
def listar_ips(engine) -> list[dict]:
    q = text("""
        SELECT i.nombre, i.red, count(*) AS atenciones, min(f.ingreso) AS desde, max(f.ingreso) AS hasta,
               round(avg(f.espera_min)::numeric, 1) AS espera_media_min
        FROM vd.fact_atencion f JOIN vd.dim_ips i USING (ips_id)
        GROUP BY i.nombre, i.red ORDER BY atenciones DESC""")
    with engine.connect() as con:
        filas = [dict(r._mapping) for r in con.execute(q)]
    for f in filas:
        f["modelable"] = f["atenciones"] >= config.MIN_REGISTROS_IPS
        f["espera_media_min"] = float(f["espera_media_min"])
        f["desde"], f["hasta"] = str(f["desde"]), str(f["hasta"])
    return filas


def _ips_id(engine, ips: str) -> int:
    with engine.connect() as con:
        v = con.execute(text("SELECT ips_id FROM vd.dim_ips WHERE nombre = :n"), {"n": ips.upper().strip()}).scalar()
    if v is None:
        raise NoEncontrado(f"No existe la IPS '{ips}'")
    return int(v)


def resumen(engine) -> dict:
    with engine.connect() as con:
        g = con.execute(text("""SELECT count(*) n, min(ingreso) d, max(ingreso) h,
                                percentile_cont(0.5) WITHIN GROUP (ORDER BY espera_min) med,
                                percentile_cont(0.9) WITHIN GROUP (ORDER BY espera_min) p90 FROM vd.fact_atencion""")).one()
        ips = con.execute(text("SELECT count(*) FROM vd.dim_ips")).scalar()
        clima = con.execute(text("SELECT count(*) FROM vd.clima_diario")).scalar()
        tri = con.execute(text("""SELECT t.nivel, count(*) n, percentile_cont(0.5) WITHIN GROUP (ORDER BY f.espera_min) med
                                  FROM vd.fact_atencion f JOIN vd.dim_triage t USING (triage_id) GROUP BY t.nivel, t.triage_id
                                  ORDER BY t.triage_id""")).all()
        hist = con.execute(text("""SELECT (floor(espera_min / 15) * 15)::int AS d, count(*) n FROM vd.fact_atencion
                                   GROUP BY 1 ORDER BY 1""")).all()
    return {"atenciones": int(g.n), "desde": str(g.d), "hasta": str(g.h), "espera_mediana_min": round(float(g.med), 1),
            "espera_p90_min": round(float(g.p90), 1), "ips": int(ips), "dias_de_clima": int(clima),
            "por_triage": [{"nivel": r.nivel, "atenciones": int(r.n), "espera_mediana_min": round(float(r.med), 1)} for r in tri],
            "histograma_espera": [{"desde": int(r.d), "n": int(r.n)} for r in hist]}


# ---------------------------------------------------------------- series y perfil real
def serie(engine, ips: str, desde: str | None, hasta: str | None, nivel: str) -> list[dict]:
    iid = _ips_id(engine, ips)
    trunc = "day" if nivel == "dia" else "hour"
    q = text(f"""SELECT date_trunc('{trunc}', hora) AS periodo, sum(llegadas)::int AS llegadas, avg(espera_media)::real AS espera_media
                 FROM vd.agg_llegadas_hora WHERE ips_id = :i AND hora >= COALESCE(CAST(:d AS timestamp), TIMESTAMP '1900-01-01') AND hora < COALESCE(CAST(:h AS timestamp), TIMESTAMP '2999-01-01')
                 GROUP BY 1 ORDER BY 1""")
    with engine.connect() as con:
        rows = con.execute(q, {"i": iid, "d": desde, "h": hasta}).all()
    return [{"t": str(r.periodo), "llegadas": r.llegadas, "espera_media": None if r.espera_media is None else round(float(r.espera_media), 1)}
            for r in rows]


def perfil_horario(engine, ips: str, desde: str = "2022-01-01") -> dict:
    iid = _ips_id(engine, ips)
    q = text("""SELECT CASE WHEN extract(isodow FROM hora) = 7 THEN 'domingo' WHEN extract(isodow FROM hora) = 6 THEN 'sabado'
                            ELSE 'laboral' END AS tipo, extract(hour FROM hora)::int AS h, avg(llegadas) AS media
                FROM (SELECT g.hora, COALESCE(a.llegadas, 0) AS llegadas
                      FROM generate_series((SELECT date_trunc('day', min(hora)) FROM vd.agg_llegadas_hora WHERE ips_id = :i AND hora >= :d),
                                           (SELECT max(hora) FROM vd.agg_llegadas_hora WHERE ips_id = :i), interval '1 hour') AS g(hora)
                      LEFT JOIN vd.agg_llegadas_hora a ON a.ips_id = :i AND a.hora = g.hora) x
                GROUP BY 1, 2 ORDER BY 1, 2""")
    with engine.connect() as con:
        rows = con.execute(q, {"i": iid, "d": desde}).all()
    out: dict = {"laboral": [0.0] * 24, "sabado": [0.0] * 24, "domingo": [0.0] * 24}
    for r in rows:
        out[r.tipo][r.h] = round(float(r.media), 2)
    return out


# ---------------------------------------------------------------- pronostico
def _modelo_vigente(engine, iid: int) -> dict:
    with engine.connect() as con:
        r = con.execute(text("""SELECT model_run_id, algoritmo, creado, train_desde, train_hasta, test_desde, test_hasta, metricas, parametros
                                FROM vd.model_run WHERE ips_id = :i AND vigente ORDER BY model_run_id DESC LIMIT 1"""), {"i": iid}).first()
    if r is None:
        raise NoEncontrado("Todavia no hay un modelo publicado para esta IPS")
    return dict(r._mapping)


def rango_fechas_pronostico(engine, ips: str) -> dict:
    iid = _ips_id(engine, ips)
    m = _modelo_vigente(engine, iid)
    return {"desde": str(m["test_desde"].date()), "hasta": str(m["test_hasta"].date())}


def pronostico_dia(engine, ips: str, fecha) -> dict:
    iid = _ips_id(engine, ips)
    m = _modelo_vigente(engine, iid)
    ini = pd.Timestamp(fecha)
    q = text("""SELECT hora, modelo, prediccion, lo80, hi80, real FROM vd.forecast_hora
                WHERE model_run_id = :m AND hora >= :a AND hora < :b ORDER BY hora""")
    with engine.connect() as con:
        rows = con.execute(q, {"m": m["model_run_id"], "a": ini.to_pydatetime(), "b": (ini + pd.Timedelta(days=1)).to_pydatetime()}).all()
    if not rows:
        r = rango_fechas_pronostico(engine, ips)
        raise NoEncontrado(f"No hay pronostico para {fecha}. Fechas disponibles: {r['desde']} a {r['hasta']}")
    horas = {h: {"hora": h, "pronostico": None, "lo80": None, "hi80": None, "real": None, "referencia": None} for h in range(24)}
    for r in rows:
        h = r.hora.hour
        if r.modelo == "vitaldata":
            horas[h].update(pronostico=round(float(r.prediccion), 3), lo80=float(r.lo80), hi80=float(r.hi80), real=int(r.real))
        elif r.modelo == "b_media_4s":
            horas[h]["referencia"] = round(float(r.prediccion), 3)
    lista = [horas[h] for h in range(24)]
    ok = [x for x in lista if x["pronostico"] is not None]
    total_p = sum(x["pronostico"] for x in ok)
    total_r = sum(x["real"] for x in ok)
    return {"ips": ips.upper(), "fecha": str(fecha), "model_run_id": m["model_run_id"], "horas": lista,
            "total_pronosticado": round(total_p, 1), "total_real": int(total_r),
            "hora_pico_pronosticada": max(ok, key=lambda x: x["pronostico"])["hora"] if ok else None,
            "hora_pico_real": max(ok, key=lambda x: x["real"])["hora"] if ok else None}


def personal_dia(engine, ips: str, fecha, servicio_min: float, meta_min: float, dotacion: int) -> dict:
    p = pronostico_dia(engine, ips, fecha)
    filas = []
    faltan = sobran = 0
    horas_criticas = 0
    for h in p["horas"]:
        lam = h["pronostico"] or 0.0
        req = cola.personal_necesario(lam, servicio_min, meta_min)
        w = cola.espera_media_min(lam, dotacion, servicio_min)
        faltan += max(0, req - dotacion)
        sobran += max(0, dotacion - req)
        critica = (not math.isfinite(w)) or w > max(meta_min * 2, 30)
        horas_criticas += int(critica)
        filas.append({"hora": h["hora"], "llegadas_esperadas": lam, "personal_necesario": req,
                      "espera_con_dotacion_min": None if not math.isfinite(w) else round(w, 1), "saturada": not math.isfinite(w),
                      "critica": critica})
    return {**{k: p[k] for k in ("ips", "fecha", "total_pronosticado", "total_real")},
            "parametros": {"servicio_min": servicio_min, "meta_min": meta_min, "dotacion": dotacion},
            "horas": filas, "horas_persona_que_faltan": faltan, "horas_persona_que_sobran": sobran, "horas_criticas": horas_criticas,
            "pico_personal": max(f["personal_necesario"] for f in filas)}


@lru_cache(maxsize=8)
def _marco(ips: str):
    from vitaldata.etl import load
    return data.preparar(load.get_engine(), ips, usar_clima=True)


@lru_cache(maxsize=8)
def _modelo_final(ips: str):
    ruta = config.MODELS_DIR / f"{slug(ips)}.joblib"
    if not ruta.exists():
        raise NoEncontrado("No hay modelo guardado para esta IPS; ejecuta la publicacion de modelos")
    return joblib.load(ruta)


def escenario(engine, req) -> dict:
    ips = req.ips.upper().strip()
    _ips_id(engine, ips)
    d = _marco(ips)
    dia = pd.Timestamp(req.fecha)
    fila = d[(d["dia"] == dia)].copy()
    if fila.empty or fila["nivel_7d"].isna().all():
        raise NoEncontrado(f"No hay datos para construir el escenario del {req.fecha}")
    modelo = _modelo_final(ips)
    base = fila.copy()
    mod = fila.copy()
    if req.lluvia_mm is not None:
        mod["lluvia_mm"] = req.lluvia_mm
        mod["log_lluvia"] = np.log1p(req.lluvia_mm)
    if req.temp_media is not None:
        mod["temp_media"] = req.temp_media
    mod["nivel_7d"] = mod["nivel_7d"] * req.factor_nivel
    mod["log_nivel"] = np.log1p(mod["nivel_7d"])
    mu_b, mu_m = modelo.predecir(base), modelo.predecir(mod)
    lo, hi = modelo.intervalo(mu_m)
    return {"ips": ips, "fecha": str(req.fecha), "nota": "Usa el modelo final ajustado con todos los datos; sirve para explorar, no para evaluar.",
            "horas": [{"hora": int(h), "base": round(float(b), 3), "escenario": round(float(m), 3), "lo80": float(l), "hi80": float(u)}
                      for h, b, m, l, u in zip(mod["hora_dia"], mu_b, mu_m, lo, hi)],
            "total_base": round(float(mu_b.sum()), 1), "total_escenario": round(float(mu_m.sum()), 1),
            "cambio_pct": round(float((mu_m.sum() / mu_b.sum() - 1) * 100), 1),
            "clima_del_dia": {"lluvia_mm": round(float(base["lluvia_mm"].iloc[0]), 1), "temp_media": round(float(base["temp_media"].iloc[0]), 1)}}


# ---------------------------------------------------------------- metricas y calidad
def metricas(engine, ips: str | None = None) -> list[dict]:
    q = """SELECT i.nombre AS ips, m.model_run_id, m.algoritmo, m.creado, m.test_desde, m.test_hasta, m.metricas, m.parametros
           FROM vd.model_run m JOIN vd.dim_ips i USING (ips_id) WHERE m.vigente"""
    params = {}
    if ips:
        q += " AND i.nombre = :n"
        params["n"] = ips.upper().strip()
    with engine.connect() as con:
        rows = [dict(r._mapping) for r in con.execute(text(q + " ORDER BY i.nombre"), params)]
    for r in rows:
        r["creado"], r["test_desde"], r["test_hasta"] = str(r["creado"]), str(r["test_desde"]), str(r["test_hasta"])
    return rows


def espera_real_ips(engine, ips: str) -> dict:
    _ips_id(engine, ips)
    return {"ips": ips.upper(), "curva": espera_real.espera_por_carga(engine, ips.upper()),
            "correlacion": espera_real.correlacion_carga_espera(engine, ips.upper())}


def calidad(engine) -> dict:
    with engine.connect() as con:
        run = con.execute(text("""SELECT etl_run_id, inicio, fin, estado, filas_extraidas, filas_duplicadas, filas_rechazadas,
                                  filas_corregidas, filas_cargadas FROM vd.etl_run WHERE flujo = 'triage_urgencias' AND estado = 'ok'
                                  AND filas_extraidas > 0 AND detalle->>'incremental' IS DISTINCT FROM 'true'
                                  ORDER BY etl_run_id DESC LIMIT 1""")).first()
        if run is None:
            return {"corrida": None, "reglas": []}
        reglas = con.execute(text("SELECT regla, severidad, filas, accion FROM vd.dq_issue WHERE etl_run_id = :r ORDER BY issue_id"),
                             {"r": run.etl_run_id}).all()
        en_fact = con.execute(text("SELECT count(*) FROM vd.fact_atencion")).scalar()
        # las cargas incrementales posteriores suman solo las filas que de verdad eran nuevas
        nuevas = con.execute(text("""SELECT COALESCE(sum(filas_cargadas), 0) FROM vd.etl_run WHERE flujo = 'triage_urgencias'
                                   AND estado = 'ok' AND etl_run_id > :r"""), {"r": run.etl_run_id}).scalar()
    esperado = run.filas_extraidas - run.filas_duplicadas - run.filas_rechazadas + int(nuevas)
    return {"corrida": {k: (str(v) if k in ("inicio", "fin") else v) for k, v in run._mapping.items()},
            "reglas": [dict(r._mapping) for r in reglas], "filas_en_base": int(en_fact),
            "conciliacion": {"extraidas": run.filas_extraidas, "menos_duplicados": run.filas_duplicadas,
                             "menos_rechazadas": run.filas_rechazadas,
                             "mas_cargas_posteriores": int(nuevas),
                             "esperado_en_base": esperado,
                             "coincide": int(en_fact) == esperado}}


def corridas(engine, limite: int = 20) -> list[dict]:
    with engine.connect() as con:
        rows = con.execute(text("""SELECT etl_run_id, flujo, inicio, fin, estado, filas_extraidas, filas_cargadas, detalle
                                   FROM vd.etl_run ORDER BY etl_run_id DESC LIMIT :n"""), {"n": limite}).all()
    return [{**dict(r._mapping), "inicio": str(r.inicio), "fin": str(r.fin) if r.fin else None} for r in rows]


# ---------------------------------------------------------------- asistente del paciente
def espera_triage(engine) -> dict:
    with engine.connect() as con:
        rows = con.execute(text("""SELECT CASE WHEN triage_id >= 4 THEN 'IV-V' WHEN triage_id = 3 THEN 'III' ELSE 'I-II' END g,
                                   percentile_cont(0.5) WITHIN GROUP (ORDER BY espera_min) m FROM vd.fact_atencion
                                   WHERE ingreso >= '2022-01-01' GROUP BY 1""")).all()
    return {r.g: round(float(r.m)) for r in rows}


def espera_por_dia(engine, dia_semana: int) -> dict:
    """Curva de espera por hora de cada centro con modelo, para un dia de la semana (0 = lunes ... 6 = domingo)."""
    con_modelo = {i["nombre"] for i in listar_ips(engine) if i["modelable"]}
    centros = [c for c in espera_real.espera_tipica_por_dia(engine, dia_semana) if c["ips"] in con_modelo]
    centros.sort(key=lambda c: c["ips"])
    return {"dia_semana": dia_semana, "centros": centros}


def responder_datos(engine, subtipo: str, ranking: list[dict], dia: int | None, hora: int) -> dict:
    """Respuestas con cifras reales del sistema para preguntas sobre la espera, la demanda y el modelo."""
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    r = resumen(engine)
    if subtipo == "espera":
        items = [f"La mitad de los pacientes espera menos de {round(r['espera_mediana_min'])} minutos y uno de cada diez espera más de {round(r['espera_p90_min'])} (datos reales de la E.S.E. Pasto Salud)."]
        if ranking:
            items.append("Para el día y la hora que elegiste: " + "; ".join(f"{x['ips'].title()} {round(x['espera_esperada_min'])} min" for x in ranking) + ".")
        return {"titulo": "Cuánto se suele esperar", "items": items}
    if subtipo == "mejor_hora" or subtipo == "pico":
        with engine.connect() as con:
            filas = con.execute(text("""SELECT extract(hour FROM ingreso)::int AS h, extract(isodow FROM ingreso)::int AS d, count(*) AS n FROM vd.fact_atencion
                                        WHERE ingreso >= '2022-01-01' GROUP BY 1, 2""")).all()
        por_hora: dict[int, int] = {}
        por_dia: dict[int, int] = {}
        for f in filas:
            por_hora[f.h] = por_hora.get(f.h, 0) + int(f.n)
            por_dia[f.d] = por_dia.get(f.d, 0) + int(f.n)
        if subtipo == "pico":
            top = sorted(por_hora, key=por_hora.get, reverse=True)[:3]
            dtop = max(por_dia, key=por_dia.get)
            return {"titulo": "Cuándo hay más gente", "items": ["Las horas con más llegadas son " + ", ".join(f"{h}:00" for h in sorted(top)) + ".", f"El día con más pacientes es el {dias[dtop - 1]}.",
                                                                  "Si puedes elegir, evita esas horas: la espera suele ser mayor."]}
        d = espera_por_dia(engine, dia if dia is not None else 0)
        mejores = []
        for hh in range(7, 21):
            vals = [c["horas"][hh]["espera_min"] for c in d["centros"] if c["horas"][hh]["espera_min"] is not None]
            if vals:
                mejores.append((min(vals), hh))
        mejores.sort()
        return {"titulo": f"Mejores horas del {dias[(dia if dia is not None else 0)]}", "items": [f"{hh}:00 (espera de unos {round(w)} minutos en el centro más corto)" for w, hh in mejores[:3]] + ["Cambia el día en la sección «¿A dónde te conviene ir?» para ver otros."]}
    if subtipo == "triage":
        nombres = {"I": "el más grave: atención inmediata", "II": "muy urgente", "III": "urgente", "IV": "menos urgente", "V": "no urgente"}
        items = ["El triage es la clasificación que se hace al llegar a urgencias para decidir a quién atender primero según la gravedad, no según quién llegó antes."]
        items += [f"Triage {x['nivel']} ({nombres.get(x['nivel'], '')}): espera mediana real de {round(x['espera_mediana_min'])} minutos." for x in r["por_triage"]]
        return {"titulo": "Qué es el triage", "items": items}
    if subtipo == "precision":
        m = metricas(engine)
        p3 = [x["metricas"]["metricas"]["3h"]["vitaldata"]["precision"] for x in m if x.get("metricas")]
        pd_ = [x["metricas"]["metricas"]["dia"]["vitaldata"]["precision"] for x in m if x.get("metricas")]
        items = ["El pronóstico usa una regresión de Poisson por hora con el tipo de día, el nivel de la última semana, la lluvia y la temperatura, y se compara con métodos simples."]
        if p3:
            items.append(f"En 53 días de prueba que el modelo nunca vio, acierta alrededor de {round(100 * sum(p3) / len(p3))} % por franja de 3 horas y {round(100 * sum(pd_) / len(pd_))} % por día.")
        items.append("La espera que ves aquí es el promedio real de 2022 para ese día y esa hora: es una guía, no una garantía.")
        return {"titulo": "Qué tan preciso es", "items": items}
    if subtipo == "fuente":
        return {"titulo": "De dónde salen los datos", "items": ["Atenciones de urgencias reales de la E.S.E. Pasto Salud (datos abiertos de datos.gov.co), de 2020 a 2022.", "Clima del IDEAM.",
                                                          f"Se analizaron {r['atenciones']:,} atenciones de {r['ips']} centros.".replace(",", "."), "No usamos datos personales de los pacientes."]}
    if subtipo == "volumen":
        return {"titulo": "Cuántos pacientes", "items": [f"{r['atenciones']:,} atenciones reales analizadas, de {r['desde'][:10]} a {r['hasta'][:10]}.".replace(",", ".")]}
    if subtipo == "centros":
        n = [i["nombre"].title() for i in listar_ips(engine) if i["modelable"]]
        return {"titulo": "Centros con datos", "items": ["Hoy el sitio compara: " + ", ".join(n) + ".", "Son centros de la E.S.E. Pasto Salud, en Pasto (Nariño)."]}
    return {"titulo": "Datos", "items": ["No tengo ese dato todavía."]}


def orientar(engine, req) -> dict:
    analisis = asistente.analizar(req.texto, getattr(req, "contexto", None))
    ranking = []
    for i in listar_ips(engine):
        if not i["modelable"]:
            continue
        w = espera_real.espera_tipica(engine, i["nombre"], req.hora, req.tipo_dia, getattr(req, "dia_semana", None))
        if w is not None:
            ranking.append({"ips": i["nombre"], "red": i["red"], "espera_esperada_min": w})
    ranking.sort(key=lambda x: x["espera_esperada_min"])
    r = asistente.construir(analisis, ranking, espera_triage(engine))
    if r["accion"] == "datos":
        d = responder_datos(engine, r["subtipo"], ranking, getattr(req, "dia_semana", None), req.hora)
        r["ficha"] = {"titulo": d["titulo"], "items": d["items"]}
        r["mensaje"] = d["titulo"]
    cond = analisis["condiciones"][0] if analisis["condiciones"] else None
    nivel = "alarma" if r["accion"] == "urgencias_ya" else (cond["nivel"] if cond else analisis["intencion"])
    return {"clasificacion": {"nivel": nivel, "categoria": cond["id"] if cond else None}, **r,
            "ranking": ranking if r.get("mostrar_ranking") else [],
            "aviso": "Prototipo academico: no reemplaza una valoracion medica. Emergencias: 123."}


# ---------------------------------------------------------------- pruebas con usuarios
def sus_puntaje(resp: list[int]) -> float:
    total = sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(resp))
    return total * 2.5


def guardar_usabilidad(engine, req) -> dict:
    sid = uuid.uuid4()
    with engine.begin() as con:
        con.execute(text("""INSERT INTO vd.usabilidad_sesion (sesion_id, rol, edad_rango, experiencia, tareas_ok, tareas_total, segundos, comentario)
                            VALUES (:s, :rol, :e, :x, :ok, :t, :seg, :c)"""),
                    {"s": sid, "rol": req.rol, "e": req.edad_rango, "x": req.experiencia, "ok": req.tareas_ok,
                     "t": req.tareas_total, "seg": req.segundos, "c": req.comentario})
        con.execute(text("""INSERT INTO vd.usabilidad_sus VALUES (:s, :q1, :q2, :q3, :q4, :q5, :q6, :q7, :q8, :q9, :q10)"""),
                    {"s": sid, **{f"q{i + 1}": v for i, v in enumerate(req.sus)}})
    return {"sesion_id": sid, "sus_puntaje": sus_puntaje(req.sus)}


def resumen_usabilidad(engine) -> dict:
    with engine.connect() as con:
        rows = con.execute(text("""SELECT s.rol, s.tareas_ok, s.tareas_total, s.segundos, u.q1, u.q2, u.q3, u.q4, u.q5, u.q6, u.q7, u.q8, u.q9, u.q10
                                   FROM vd.usabilidad_sesion s JOIN vd.usabilidad_sus u USING (sesion_id)""")).all()
    if not rows:
        return {"sesiones": 0}
    sus = [sus_puntaje([getattr(r, f"q{i}") for i in range(1, 11)]) for r in rows]
    n = len(rows)
    media = float(np.mean(sus))
    ee = float(np.std(sus, ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    ok = sum(r.tareas_ok for r in rows) / sum(r.tareas_total for r in rows)
    return {"sesiones": n, "sus_media": round(media, 1), "sus_ic95": [round(media - 1.96 * ee, 1), round(media + 1.96 * ee, 1)],
            "tareas_completadas": round(ok, 3), "segundos_mediana": float(np.median([r.segundos for r in rows])),
            "por_rol": {rol: sum(1 for r in rows if r.rol == rol) for rol in {r.rol for r in rows}},
            "referencia": "Un puntaje SUS de 68 es el promedio de la industria; sobre 80 es muy bueno."}
