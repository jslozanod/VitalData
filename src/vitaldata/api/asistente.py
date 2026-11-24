"""Asistente del paciente. Son reglas simples y transparentes, no un sistema clinico ni un modelo de lenguaje.

Hace tres cosas: (1) reconoce senales de alarma y manda a pedir ayuda; (2) para sintomas comunes da orientacion general de
autocuidado, que se suele usar sin formula y cuando consultar (ver conocimiento.py); (3) dice a que centro conviene ir segun la
espera real de cada uno a esa hora. Lo unico que viene de los datos es la espera esperada de cada IPS y lo que tardan los
niveles de triage. No hace diagnosticos."""
from __future__ import annotations

import difflib
import re
import unicodedata

from . import conocimiento

ALARMA = [
    r"dolor (de|en el|en mi) pecho", r"duele (el|mi) pecho", r"pecho me duele", r"opresion en el pecho", r"no (puedo|logro) respirar", r"me cuesta respirar",
    r"falta (el )?aire", r"me ahogo", r"ahog", r"desmay", r"convuls",
    r"sangrado (abundante|que no para)", r"vomit\w* sangre", r"sangre en (las )?heces", r"heces negras", r"paralis", r"cara (torcida|caida)", r"no (siento|puedo mover)",
    r"perdi (el )?conocimiento", r"inconsciente", r"herida profunda", r"quemadura (grande|grave)", r"envenen", r"intoxic",
    r"embarazada.*(sangrado|dolor fuerte)", r"pensamientos? de (morir|quitarme)", r"quiero (morir|hacerme dano)", r"(dolor|presion) (fuerte|intenso) en el pecho",
    r"golpe fuerte en la cabeza", r"peor dolor de (mi vida|cabeza)", r"hinchazon (de|en) (los |las |la |el )?(labios|lengua|garganta|cara)", r"labios morados",
    r"se me (hincho|inflamo) (la |los |el )?(lengua|labios|cara|garganta)", r"(lengua|labios|garganta) (hinchad|inflamad)",
]
LEVE = [
    r"\bgripa\b", r"\bgripe\b", r"resfri", r"tos\b", r"dolor de garganta", r"estornud", r"congestion", r"fiebre leve",
    r"dolor de cabeza leve", r"malestar", r"diarrea leve", r"\bnauseas?\b leves?", r"dolor muscular", r"picadura",
    r"alergia leve", r"dolor de oido", r"conjuntivitis", r"(torcedura|esguince) leve", r"formula|receta|control",
]
CATEGORIAS = {
    "respiratorio": [r"tos\b", r"gripa|gripe|resfri", r"garganta", r"respir", r"asma"],
    "digestivo": [r"diarrea", r"vomit", r"nauseas?", r"estomag", r"abdomin", r"barriga"],
    "trauma": [r"golpe", r"caida|me cai", r"fractura", r"esguince|torcedura", r"herida", r"corte"],
    "fiebre": [r"fiebre", r"temperatura alta"],
}
PRIORIDAD = {"consulta_pronto": 0, "leve": 1}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _hay(patrones: list[str], t: str) -> bool:
    return any(re.search(p, t) for p in patrones)


def clasificar(texto: str) -> dict:
    t = _norm(texto)
    if len(t.strip()) < 3:
        return {"nivel": "sin_informacion", "categoria": None}
    if _hay([_norm(p) for p in ALARMA], t):
        return {"nivel": "alarma", "categoria": None}
    cat = next((c for c, pats in CATEGORIAS.items() if _hay([_norm(p) for p in pats], t)), "otro")
    leve = _hay([_norm(p) for p in LEVE], t)
    return {"nivel": "leve" if leve else "indeterminado", "categoria": cat}


def respuesta(clase: dict, ranking: list[dict], espera_triage: dict) -> dict:
    """Respuesta basica segun el nivel (se conserva para pruebas y para el modo sin API)."""
    nivel = clase["nivel"]
    if nivel == "alarma":
        return {"accion": "urgencias_ya",
                "mensaje": "Por lo que cuentas, no esperes ni compares clinicas: llama al 123 o ve de inmediato a la urgencia mas cercana.",
                "mostrar_ranking": False}
    if nivel == "sin_informacion":
        return {"accion": "pedir_mas_datos", "mensaje": "Cuentame un poco mas: que sientes y desde cuando.", "mostrar_ranking": False}
    mejor = ranking[0] if ranking else None
    if nivel == "leve":
        iv = espera_triage.get("IV-V")
        iii = espera_triage.get("III")
        comparacion = (f" En los datos reales, quienes llegan con una urgencia menor (triage IV o V) esperan en promedio {iv} minutos, "
                       f"frente a {iii} minutos en triage III.") if iv and iii else ""
        return {"accion": "orientacion_leve",
                "mensaje": "Lo que describes parece leve. Antes de ir a urgencias puedes pedir una cita prioritaria o una teleconsulta." + comparacion
                           + " Si empeoras o aparece algun sintoma de alarma, ve a urgencias.",
                "mostrar_ranking": True, "mejor": mejor}
    return {"accion": "orientacion_general",
            "mensaje": "No puedo valorar eso por aqui. Si te preocupa, consulta; esta es la urgencia con menos espera esperada ahora."
                       + " Si hay dificultad para respirar, dolor fuerte en el pecho o perdida de conocimiento, llama al 123.",
            "mostrar_ranking": True, "mejor": mejor}


# ---------------------------------------------------------------------------------------- conversacion
def _flags(t: str) -> dict:
    return {
        "bebe": bool(re.search(r"\bbebe\b|recien nacido|\b\d+ meses? de (nacido|edad)|mi bebe", t)),
        "nino": bool(re.search(r"\bnin[oa]s?\b|\bmi hij[oa]\b|\bpequen[oa]\b|\bhijito|\bhijita", t)),
        "embarazo": bool(re.search(r"embarazad|gestante|estoy en embarazo", t)),
        "mayor": bool(re.search(r"adulto mayor|abuel[oa]|anciano|\bmi (papa|mama) de \d{2}", t)),
    }


_PALABRAS_COMUNES = {"dolor", "tengo", "tiene", "tener", "como", "cuando", "puedo", "hacer", "estoy", "siento", "mucho", "mucha", "problema", "problemas", "sobre", "para", "desde", "porque", "cuanto"}


def _fon(w: str) -> str:
    """Forma fonetica simple del espanol, para tolerar errores como cavesa por cabeza."""
    w = re.sub(r"qu", "k", w)
    w = re.sub(r"c(?=[ei])", "s", w)
    w = w.replace("c", "k").replace("z", "s").replace("v", "b").replace("h", "").replace("ll", "y").replace("w", "b")
    return re.sub(r"(.)+", r"", w)


def _construir_vocabulario() -> dict:
    """Palabras clave de cada tema (sacadas de sus patrones): forma fonetica -> id del tema."""
    candidatos: dict[str, list] = {}
    for c in conocimiento.CONDICIONES:
        for p in c["patrones"]:
            for w in re.findall(r"[a-z]{5,}", re.sub(r"\[a-z]", " ", p)):
                if w not in _PALABRAS_COMUNES:
                    candidatos.setdefault(w, []).append(c)
    vocab = {}
    for w, cs in candidatos.items():
        propios = [c for c in cs if w in _norm(c["nombre"]) or w in c["id"]]
        vocab[_fon(w)] = ((propios or cs)[0]["id"], w)
    return vocab


_VOCAB: dict | None = None


def _fuzzy(t: str) -> list[dict]:
    global _VOCAB
    if _VOCAB is None:
        _VOCAB = _construir_vocabulario()
    ids: list[str] = []
    for tok in re.findall(r"[a-z]{5,}", t):
        f = _fon(tok)
        if tok in _PALABRAS_COMUNES:
            continue
        if f in _VOCAB:                                           # suena igual pero se escribe distinto (cavesa / cabeza)
            if _VOCAB[f][1] != tok and _VOCAB[f][0] not in ids:
                ids.append(_VOCAB[f][0])
            continue
        cerca = [x for x in difflib.get_close_matches(f, list(_VOCAB), n=3, cutoff=0.84) if x[0] == f[0]]     # un error de escritura casi nunca cambia la primera letra
        if cerca and _VOCAB[cerca[0]][0] not in ids:
            ids.append(_VOCAB[cerca[0]][0])
    return [c for c in conocimiento.CONDICIONES if c["id"] in ids]


def _buscar(lista: list[dict], t: str) -> list[dict]:
    return [x for x in lista if _hay(x["patrones"], t)]


def analizar(texto: str, contexto: str | None = None) -> dict:
    """Entiende el mensaje: alarma, sintomas, medicamentos, tramites, preguntas sobre los datos o conversacion basica."""
    t = _norm(texto).strip()
    if len(t) < 3:
        return {"intencion": "sin_informacion", "condiciones": [], "flags": {}}
    flags = _flags(t)
    ctx = next((c for c in conocimiento.CONDICIONES if c["id"] == contexto), None) if contexto else None
    if _hay([_norm(p) for p in ALARMA], t):
        return {"intencion": "alarma", "condiciones": [], "flags": flags}
    meds = _buscar(conocimiento.MEDICAMENTOS, t)
    if _hay(conocimiento.INTENCIONES["dosis"], t):
        return {"intencion": "dosis", "condiciones": [], "flags": flags, "medicamentos": meds}
    conds = [c for c in conocimiento.CONDICIONES if _hay(c["patrones"], t)]
    pregunta_med = bool(re.search(r"puedo tomar|para que sirve|que es |sirve|efectos|contraindic|se puede|combinar|tomar|mezclar|riesgos", t))
    if meds and (not conds or pregunta_med):
        return {"intencion": "medicamento", "condiciones": [], "flags": flags, "medicamentos": meds}
    for nombre, pats in conocimiento.DATOS.items():
        if _hay(pats, t):
            return {"intencion": "datos", "subtipo": nombre, "condiciones": [], "flags": flags}
    info = _buscar(conocimiento.INFO, t)
    if info and not conds:
        return {"intencion": "info", "condiciones": [], "flags": flags, "info": info[0]}
    if conds:
        conds.sort(key=lambda c: PRIORIDAD[c["nivel"]])          # estable: conserva el orden de la lista a igual prioridad
        if flags["bebe"] and any(c["id"] == "fiebre" for c in conds):
            return {"intencion": "alarma_bebe", "condiciones": conds, "flags": flags}
        return {"intencion": "sintomas", "condiciones": conds, "flags": flags}
    for nombre in ("ctx_casa", "ctx_consultar", "ctx_alarma", "ctx_especialista", "medicina_sin_sintoma"):
        if _hay(conocimiento.INTENCIONES[nombre], t):
            if ctx:
                return {"intencion": "contexto", "subtipo": nombre, "condiciones": [ctx], "flags": flags}
            return {"intencion": "medicina_sin_sintoma", "condiciones": [], "flags": flags}
    for nombre, pats in conocimiento.INTENCIONES.items():
        if nombre in ("dosis", "ctx_casa", "ctx_consultar", "ctx_alarma", "ctx_especialista"):
            continue
        if _hay(pats, t):
            return {"intencion": nombre, "condiciones": [], "flags": flags}
    parecidos = _fuzzy(t)
    if parecidos:
        parecidos.sort(key=lambda c: PRIORIDAD[c["nivel"]])
        return {"intencion": "sintomas", "condiciones": parecidos, "flags": flags, "aproximado": True}
    return {"intencion": "no_entendido", "condiciones": [], "flags": flags}


def _cierre_flags(flags: dict) -> str:
    extra = []
    if flags.get("nino") or flags.get("bebe"):
        extra.append("Si es para un niño, consulta con el pediatra antes de darle cualquier medicamento.")
    if flags.get("embarazo"):
        extra.append("Estando embarazada, consulta con tu médico antes de tomar cualquier medicamento.")
    if flags.get("mayor"):
        extra.append("En adultos mayores conviene consultar pronto y antes de tomar medicamentos.")
    return " ".join(extra)


def construir(analisis: dict, ranking: list[dict], espera_triage: dict) -> dict:
    """Arma la respuesta completa para el chat a partir del analisis y del ranking de esperas."""
    it = analisis["intencion"]
    mejor = ranking[0] if ranking else None
    temas = conocimiento.TEMAS_RAPIDOS
    base = {"accion": "conversacion", "mostrar_ranking": False, "guia": None, "tambien": [], "sugerencias": []}

    if it == "alarma":
        return {**base, "accion": "urgencias_ya",
                "mensaje": "Por lo que cuentas, no esperes ni compares clínicas: llama al 123 o ve de inmediato a la urgencia más cercana."}
    if it == "alarma_bebe":
        return {**base, "accion": "urgencias_ya",
                "mensaje": "Un bebé con fiebre debe ser visto de inmediato. No esperes ni compares clínicas: llama al 123 o ve ya a la urgencia más cercana."}
    if it == "sin_informacion":
        return {**base, "accion": "pedir_mas_datos", "mensaje": "Cuéntame un poco más: qué sientes y desde cuándo.", "sugerencias": temas}
    if it == "dosis":
        nombres = ", ".join(m["nombre"] for m in analisis.get("medicamentos", []))
        return {**base, "accion": "conversacion", "sugerencias": ["Para qué sirve un medicamento", "Reservar cita"],
                "mensaje": ("No puedo indicar dosis" + (f" de {nombres}" if nombres else "") + ": dependen de la edad, el peso, otras enfermedades y los demás medicamentos que tomes, y un error puede ser peligroso. "
                            "Sigue la etiqueta o el prospecto, o pregúntale a un farmacéutico o a tu médico. Si es para un niño, solo con indicación del pediatra.")}
    if it == "medicamento":
        m = analisis["medicamentos"][0]
        otros = [x["nombre"] for x in analisis["medicamentos"][1:]]
        return {**base, "accion": "medicamento", "ficha": {"titulo": m["nombre"], "subtitulo": m["para_que"], "items": m["precauciones"], "aviso": conocimiento.AVISO_MEDICAMENTOS},
                "mensaje": f"{m['nombre']}: {m['para_que']}" + (f" También mencionaste: {', '.join(otros)}." if otros else "") + " No indico dosis; sigue la etiqueta o la indicación de tu médico.",
                "sugerencias": ["Cuándo consultar", "Reservar cita", "Nueva consulta"]}
    if it == "info":
        f = analisis["info"]
        return {**base, "accion": "informacion", "ficha": {"titulo": f["titulo"], "items": f["items"]}, "mensaje": f["titulo"], "sugerencias": ["Reservar cita"]}
    if it == "datos":
        return {**base, "accion": "datos", "subtipo": analisis["subtipo"], "mostrar_ranking": analisis["subtipo"] in ("espera", "mejor_centro"), "mejor": mejor, "mensaje": ""}
    if it == "contexto":
        c = analisis["condiciones"][0]
        sub = analisis["subtipo"]
        if sub == "medicina_sin_sintoma":
            t, items, aviso = "Qué se suele tomar", c["medicamentos"], conocimiento.AVISO_MEDICAMENTOS
        elif sub == "ctx_consultar":
            t, items, aviso = "Pide una cita o consulta si…", c["consultar_si"], None
        elif sub == "ctx_alarma":
            t, items, aviso = "Ve a urgencias o llama al 123 si…", c["alarma"], None
        elif sub == "ctx_especialista":
            t, items, aviso = f"Para este tema: {c['especialidad']}", [f"La cita suele ser con {c['especialidad']}.", "Si no sabes con quién, pide una cita de medicina general: te orientan."], None
        else:
            t, items, aviso = "Qué hacer en casa", c["casa"], None
        guia = {k: c[k] for k in ("id", "nombre", "especialidad", "casa", "medicamentos", "consultar_si", "alarma")}
        guia["aviso_medicamentos"] = conocimiento.AVISO_MEDICAMENTOS
        return {**base, "accion": "contexto", "guia": guia, "ficha": {"titulo": f"{t} ({c['nombre'].lower()})", "items": items, "aviso": aviso}, "mensaje": f"Sobre {c['nombre'].lower()}:",
                "sugerencias": ["Qué hacer en casa", "Qué puedo tomar", "Cuándo consultar", "Señales de alarma", "Reservar cita"]}
    if it == "sintomas":
        c = analisis["condiciones"][0]
        otras = [x["nombre"] for x in analisis["condiciones"][1:]]
        if c["nivel"] == "consulta_pronto":
            accion_txt = " Te conviene que te vea un profesional pronto: pide una cita prioritaria hoy o mañana. Si aparece una señal de alarma, ve a urgencias."
            accion = "consulta_pronto"
        else:
            accion_txt = " Puedes empezar con cuidados en casa; si no mejoras o aparece una señal de alarma, pide una cita prioritaria o una teleconsulta."
            accion = "orientacion_leve"
        msg = ("Entendí que hablas de: " + c["nombre"].lower() + ". " if analisis.get("aproximado") else "") + c["resumen"] + accion_txt
        if otras:
            msg += " También mencionaste: " + ", ".join(otras).lower() + "."
        cierre = _cierre_flags(analisis["flags"])
        if cierre:
            msg += " " + cierre
        guia = {k: c[k] for k in ("id", "nombre", "especialidad", "casa", "medicamentos", "consultar_si", "alarma")}
        guia["aviso_medicamentos"] = conocimiento.AVISO_MEDICAMENTOS
        return {**base, "accion": accion, "mensaje": msg, "mostrar_ranking": True, "guia": guia, "tambien": otras, "mejor": mejor,
                "sugerencias": ["Qué hacer en casa", "Qué puedo tomar", "Cuándo consultar", "Señales de alarma", "Reservar cita"]}
    if it == "saludo":
        return {**base, "mensaje": "Hola, soy el asistente de VitalData. Cuéntame qué sientes y te digo qué puedes hacer en casa, qué se suele tomar y a qué centro te conviene ir según la espera. ¿Qué te pasa?",
                "sugerencias": temas}
    if it == "gracias":
        return {**base, "mensaje": "Con gusto. Si te sientes peor o aparece una señal de alarma, ve a urgencias o llama al 123. ¿Quieres contarme otro síntoma?", "sugerencias": temas}
    if it == "despedida":
        return {**base, "mensaje": "Cuídate mucho. Si empeoras, ve a urgencias o llama al 123."}
    if it == "ayuda":
        return {**base, "mensaje": ("Puedo ayudarte con tres cosas: decirte qué hacer en casa con síntomas comunes, contarte qué medicamentos de venta libre se suelen usar y cuándo consultar, "
                                    "y decirte a qué centro conviene ir según el día y la hora. No hago diagnósticos ni reemplazo a un médico."), "sugerencias": temas}
    if it == "cita":
        return {**base, "accion": "orientacion_cita", "mostrar_ranking": True, "mejor": mejor,
                "mensaje": "Para pedir tu cita usa el calendario de «Reserva tu cita» en esta página. Y si quieres decidir a qué centro ir, mira la sección «¿A dónde te conviene ir?», que muestra la espera típica de cada uno según el día y la hora."}
    if it == "datos_contacto":
        return {**base, "mostrar_ranking": True, "mejor": mejor,
                "mensaje": "No tengo direcciones, teléfonos ni horarios de los centros: los publica cada uno. En la sección «¿A dónde te conviene ir?» puedes ver cuál suele tener menos espera."}
    if it == "medicina_sin_sintoma":
        return {**base, "mensaje": "Para decirte qué suele usarse, cuéntame primero qué síntoma tienes, por ejemplo fiebre, dolor de cabeza o gripa.", "sugerencias": temas}
    return {**base, "accion": "orientacion_general", "mostrar_ranking": True, "mejor": mejor, "sugerencias": temas + ["Reservar cita"],
            "mensaje": ("No tengo ese tema entre los que sé explicar, y prefiero no inventar. Cuéntame con otras palabras qué sientes y desde cuándo, o reserva una cita con un profesional que pueda valorarte. "
                        "Si hay dificultad para respirar, dolor fuerte en el pecho o pérdida de conocimiento, llama al 123.")}
