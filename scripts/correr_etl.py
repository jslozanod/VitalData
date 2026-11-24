"""Linea de comandos del ETL.

    python scripts/correr_etl.py --init            crea las tablas
    python scripts/correr_etl.py --triage          baja todo de la API y carga
    python scripts/correr_etl.py --triage --archivo data/raw/pasto_triage_urgencias_raw.csv
    python scripts/correr_etl.py --clima           clima diario del IDEAM para Pasto
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vitaldata.etl import load, pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
p = argparse.ArgumentParser()
p.add_argument("--init", action="store_true")
p.add_argument("--triage", action="store_true")
p.add_argument("--clima", action="store_true")
p.add_argument("--archivo", type=Path)
p.add_argument("--desde")
a = p.parse_args()
logging.getLogger("httpx").setLevel(logging.WARNING)   # no llenar el registro con cada peticion
eng = load.get_engine()
if a.init:
    load.init_schema(eng)
    print("esquema listo")
if a.triage:
    print(json.dumps(pipeline.flujo_triage(eng, desde=a.desde, desde_archivo=a.archivo), indent=2, default=str))
if a.clima:
    print(json.dumps(pipeline.flujo_clima(eng), indent=2, default=str))
