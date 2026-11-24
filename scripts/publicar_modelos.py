"""Reentrena, evalua en el periodo de prueba y guarda metricas y pronosticos en PostgreSQL.

    python scripts/publicar_modelos.py
"""
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vitaldata.etl import load  # noqa: E402
from vitaldata.models import publicar  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
eng = load.get_engine()
resultados = publicar.publicar_todo(eng)
for r in resultados:
    m = r["metricas"]
    print(f"{r['ips']}: precision 3h = {m['3h']['vitaldata']['precision']:.1%}  "
          f"(referencia {r['mejor_referencia']}: {m['3h'][r['mejor_referencia']]['precision']:.1%}), "
          f"cobertura 80% = {m['cobertura_80']:.1%}")
print(json.dumps([{k: v for k, v in r.items() if k != "metricas"} for r in resultados], indent=2, default=str))
