"""Exporta lo que muestra la pagina a archivos JSON, para que la pagina tambien funcione sin servidor
(se abre el index.html directamente o se publica como pagina estatica). Los numeros salen de la misma base y la misma API."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from vitaldata import config
from vitaldata.api import service
from vitaldata.models import espera_real
from vitaldata.models.publicar import slug


def _guardar(ruta: Path, obj) -> None:
    ruta.write_text(json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":")), encoding="utf-8")


def snapshot(engine, salida: Path) -> dict:
    """Escribe web/data/snapshot.js: un solo archivo que la pagina carga con <script>, asi funciona incluso abierta desde el disco."""
    salida.mkdir(parents=True, exist_ok=True)
    snap: dict = {}
    _guardar = lambda ruta, obj: snap.__setitem__(ruta.stem, obj)   # noqa: E731
    ips_lista = service.listar_ips(engine)
    for i in ips_lista:
        if i["modelable"]:
            try:
                i["rango_pronostico"] = service.rango_fechas_pronostico(engine, i["nombre"])
            except service.NoEncontrado:
                i["rango_pronostico"] = None
    _guardar(salida / "ips.json", ips_lista)
    _guardar(salida / "resumen.json", service.resumen(engine))
    _guardar(salida / "metricas.json", service.metricas(engine))
    _guardar(salida / "calidad.json", service.calidad(engine))
    _guardar(salida / "corridas.json", service.corridas(engine, 30))
    _guardar(salida / "usabilidad_resumen.json", service.resumen_usabilidad(engine))
    _guardar(salida / "espera_triage.json", service.espera_triage(engine))
    n_dias = 0
    tipica = {}
    for i in ips_lista:
        if not i["modelable"] or not i.get("rango_pronostico"):
            continue
        s = slug(i["nombre"])
        tipica[i["nombre"]] = {t: [espera_real.espera_tipica(engine, i["nombre"], h, t) for h in range(24)] for t in ("laboral", "sabado", "domingo")}
        _guardar(salida / f"perfil_{s}.json", service.perfil_horario(engine, i["nombre"]))
        _guardar(salida / f"espera_real_{s}.json", service.espera_real_ips(engine, i["nombre"]))
        _guardar(salida / f"serie_dia_{s}.json", service.serie(engine, i["nombre"], None, None, "dia"))
        dias = {}
        for f in pd.date_range(i["rango_pronostico"]["desde"], i["rango_pronostico"]["hasta"]):
            try:
                p = service.pronostico_dia(engine, i["nombre"], f.date())
                dias[str(f.date())] = {"h": [[h["pronostico"], h["lo80"], h["hi80"], h["real"], h["referencia"]] for h in p["horas"]],
                                       "tp": p["total_pronosticado"], "tr": p["total_real"]}
            except service.NoEncontrado:
                continue
        _guardar(salida / f"pronostico_{s}.json", dias)
        n_dias += len(dias)
    _guardar(salida / "espera_tipica.json", tipica)
    ev = config.ROOT / "docs" / "evidencias"
    for nombre in ("pruebas", "benchmark", "consultas", "airflow", "accesibilidad"):
        f = ev / f"{nombre}.json"
        if f.exists():
            snap[f"ev_{nombre}"] = json.loads(f.read_text(encoding="utf-8"))
    (salida / "snapshot.js").write_text("window.SNAPSHOT=" + json.dumps(snap, ensure_ascii=False, default=str, separators=(",", ":")) + ";",
                                        encoding="utf-8")
    return {"ips": [i["nombre"] for i in ips_lista if i["modelable"]], "dias_de_pronostico": n_dias,
            "archivo": str(salida / "snapshot.js"), "kb": round((salida / "snapshot.js").stat().st_size / 1024)}
