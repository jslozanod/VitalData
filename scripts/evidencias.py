"""Genera las evidencias que muestra la pagina, ejecutando de verdad cada comprobacion.

    python scripts/evidencias.py pruebas      pytest con cobertura -> docs/evidencias/pruebas.json
    python scripts/evidencias.py consultas    EXPLAIN ANALYZE con y sin indice -> docs/evidencias/consultas.json
    python scripts/evidencias.py benchmark    latencia de la API (p50, p95) -> docs/evidencias/benchmark.json
"""
import json
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EV = RAIZ / "docs" / "evidencias"
sys.path.insert(0, str(RAIZ / "src"))
EV.mkdir(parents=True, exist_ok=True)


def pruebas():
    salida = EV / "pytest_salida.txt"
    xml = EV / "pytest_junit.xml"
    cmd = [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "-p", "no:cacheprovider", "-W", "ignore",
           f"--junitxml={xml}", "--cov=vitaldata", "--cov-report=term", "--cov-report=json:" + str(EV / "cobertura.json")]
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(RAIZ / "src")})
    salida.write_text(r.stdout + r.stderr, encoding="utf-8")
    import xml.etree.ElementTree as ET
    raiz = ET.parse(xml).getroot()
    por_archivo: dict = {}
    for caso in raiz.iter("testcase"):
        arch = caso.get("classname", "").rsplit(".", 1)[0].replace(".", "/") + ".py"
        d = por_archivo.setdefault(arch, {"archivo": arch, "passed": 0, "failed": 0})
        if caso.find("failure") is not None or caso.find("error") is not None:
            d["failed"] += 1
        elif caso.find("skipped") is None:
            d["passed"] += 1
    total = sum(d["passed"] + d["failed"] for d in por_archivo.values())
    pasaron = sum(d["passed"] for d in por_archivo.values())
    cob = json.loads((EV / "cobertura.json").read_text(encoding="utf-8"))["totals"]["percent_covered"]
    res = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "total": total, "passed": pasaron, "failed": total - pasaron,
           "cobertura": round(cob, 1), "por_archivo": sorted(por_archivo.values(), key=lambda x: x["archivo"])}
    (EV / "pruebas.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_archivo"}))


def consultas():
    from sqlalchemy import text
    from vitaldata.etl import load
    eng = load.get_engine()
    casos = [
        ("Llegadas de una IPS en un mes", "Lo que pide el modelo para armar una serie: una IPS y un rango de fechas en la tabla de hechos.",
         "SELECT date_trunc('hour', ingreso), count(*) FROM vd.fact_atencion WHERE ips_id = {iid} AND ingreso >= '2022-06-01' AND ingreso < '2022-07-01' GROUP BY 1",
         "ix_fact_ips_ingreso", "CREATE INDEX ix_fact_ips_ingreso ON vd.fact_atencion (ips_id, ingreso)"),
        ("Espera tipica por hora del dia", "Lo que usa el asistente: espera media de una IPS a una hora, en 2022.",
         "SELECT avg(espera_min) FROM vd.fact_atencion WHERE ips_id = {iid} AND ingreso >= '2022-01-01' AND extract(hour FROM ingreso) = 10",
         "ix_fact_ips_ingreso", "CREATE INDEX ix_fact_ips_ingreso ON vd.fact_atencion (ips_id, ingreso)"),
    ]
    resultados = []
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as con:
        iid = con.execute(text("SELECT ips_id FROM vd.dim_ips WHERE nombre = 'CENTRO HOSPITAL LA ROSA'")).scalar()
        for nombre, desc, sql, idx, crear in casos:
            sql = sql.format(iid=iid)
            def medir():
                tiempos, plan = [], ""
                for _ in range(5):
                    filas = [r[0] for r in con.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + sql))]
                    tiempos.append(float(re.search(r"Execution Time: ([\d.]+) ms", "\n".join(filas)).group(1)))
                    plan = "\n".join(filas)
                return statistics.median(tiempos), plan
            con.execute(text(f"DROP INDEX IF EXISTS vd.{idx}"))
            con.execute(text("ANALYZE vd.fact_atencion"))
            sin, plan_sin = medir()
            con.execute(text(crear))
            con.execute(text("ANALYZE vd.fact_atencion"))
            con_i, plan_con = medir()
            resultados.append({"nombre": nombre, "descripcion": desc, "sin_indice_ms": round(sin, 2), "con_indice_ms": round(con_i, 2),
                               "mejora": round(sin / con_i, 1), "plan_sin_indice": plan_sin.splitlines()[0:6], "plan_con_indice": plan_con.splitlines()[0:6]})
    out = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "filas_en_hechos": None, "consultas": resultados}
    with eng.connect() as con:
        out["filas_en_hechos"] = con.execute(text("SELECT count(*) FROM vd.fact_atencion")).scalar()
    (EV / "consultas.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in resultados:
        print(r["nombre"], r["sin_indice_ms"], "->", r["con_indice_ms"], "ms")


def benchmark(n=60):
    from fastapi.testclient import TestClient
    from vitaldata.api.main import app
    c = TestClient(app)
    ips = c.get("/api/ips").json()
    base = next(i for i in ips if i.get("modelable") and i.get("rango_pronostico"))
    fecha, nombre = base["rango_pronostico"]["desde"], base["nombre"]
    rutas = {
        "/api/resumen": ("GET", "/api/resumen", None),
        "/api/pronostico": ("GET", f"/api/pronostico?ips={nombre}&fecha={fecha}", None),
        "/api/personal": ("GET", f"/api/personal?ips={nombre}&fecha={fecha}", None),
        "/api/orientar": ("POST", "/api/orientar", {"texto": "tengo gripa", "hora": 10}),
    }
    todos, por_ruta = [], {}
    for k, (m, u, b) in rutas.items():
        t = []
        for _ in range(n):
            t0 = time.perf_counter()
            r = c.get(u) if m == "GET" else c.post(u, json=b)
            assert r.status_code == 200, (k, r.status_code, r.text[:100])
            t.append((time.perf_counter() - t0) * 1000)
        t.sort()
        por_ruta[k] = {"mediana_ms": round(statistics.median(t), 1), "p95_ms": round(t[int(len(t) * 0.95) - 1], 1)}
        todos += t
    todos.sort()
    res = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "peticiones": len(todos), "mediana_ms": round(statistics.median(todos), 1),
           "p95_ms": round(todos[int(len(todos) * 0.95) - 1], 1), "por_ruta": por_ruta,
           "nota": "Medido con el cliente de pruebas de FastAPI contra PostgreSQL local; sin red de por medio."}
    (EV / "benchmark.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res))


if __name__ == "__main__":
    {"pruebas": pruebas, "consultas": consultas, "benchmark": benchmark}[sys.argv[1]]()
