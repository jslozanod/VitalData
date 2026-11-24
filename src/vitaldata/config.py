"""Configuracion central. Las credenciales salen de variables de entorno o del archivo .env (nunca del codigo)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _cargar_env():
    ruta = ROOT / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://vitaldata:vd_local_2026@localhost:5433/vitaldata"
)
SOCRATA_BASE = "https://www.datos.gov.co/resource"
SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN") or None

# Conjuntos de datos abiertos (datos.gov.co)
DS_TRIAGE = "vt5n-eu2r"     # Clasificacion en triage de urgencias, E.S.E. Pasto Salud
DS_LLUVIA = "s54a-sgyg"     # IDEAM: precipitacion
DS_TEMP = "sbwg-7ju4"       # IDEAM: temperatura ambiente del aire

# Estacion del IDEAM en Pasto que usamos para el clima (Universidad de Narino, zona urbana)
ESTACION_CLIMA = "0052045080"

# De abril de 2020 a marzo de 2021 la fuente no trae registros: el periodo continuo empieza en abril de 2021
INICIO_PERIODO_CONTINUO = "2021-04-01"
MIN_REGISTROS_IPS = 5000

RAW_DIR = ROOT / "data" / "raw"
MODELS_DIR = ROOT / "models_store"
