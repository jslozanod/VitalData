"""Fixtures compartidas. Las pruebas de integracion usan una base de datos aparte (vitaldata_test) para no tocar los datos reales."""
import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from vitaldata import config
from vitaldata.etl import load

ADMIN_URL = config.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
TEST_URL = config.DATABASE_URL.rsplit("/", 1)[0] + "/vitaldata_test"


@pytest.fixture(scope="session")
def engine_prueba():
    """Base vacia y con el esquema real, creada para las pruebas."""
    try:
        admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with admin.connect() as con:
            existe = con.execute(text("SELECT 1 FROM pg_database WHERE datname = 'vitaldata_test'")).scalar()
            if not existe:
                con.execute(text("CREATE DATABASE vitaldata_test"))
    except OperationalError:
        pytest.skip("PostgreSQL no esta disponible (docker compose up -d db)")
    eng = load.get_engine(TEST_URL)
    with eng.begin() as con:
        con.exec_driver_sql("DROP SCHEMA IF EXISTS vd CASCADE")
    load.init_schema(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def crudo_pequeno() -> pd.DataFrame:
    """Diez filas con la misma forma que la API de Pasto Salud, incluidas las trampas conocidas."""
    base = {"codadminis": "ESS118", "nom_admini": "EMSSANAR S.A.S", "red": "RED NORTE", "ips": "HOSPITAL LOCAL CIVIL"}
    filas = [
        ("2021-05-03T08:29:02.367", "2021-05-03T08:36:00.000", "III"),
        ("2021-05-03T08:29:02.367", "2021-05-03T08:36:00.000", "III"),          # duplicado exacto
        ("2021-05-03T09:10:30.100", "2021-05-03T09:10:00.000", "IV"),          # espera negativa por redondeo
        ("2021-05-03T10:00:00.000", "2021-05-03T11:30:00.000", "III"),
        ("2021-05-03T11:00:00.000", "2021-05-03T11:20:00.000", "II"),
        ("2021-05-03T12:00:00.000", "2021-05-03T11:00:00.000", "III"),         # atencion antes del ingreso: se rechaza
        ("2021-05-03T13:00:00.000", "2021-05-03T14:00:00.000", "IX"),          # triage invalido: se rechaza
        ("fecha mala", "2021-05-03T14:00:00.000", "III"),                      # fecha invalida: se rechaza
        ("2021-05-04T07:15:00.000", "2021-05-04T07:45:00.000", "V"),
        ("2021-05-04T07:40:00.000", "2021-05-05T09:00:00.000", "III"),         # mas de 24 h: se rechaza
    ]
    return pd.DataFrame([{**base, "fecha_ing": a, "hora_ingre": "1900-01-01T00:00:00.000", "fecha_atencion": b,
                          "hora_atencion": "1900-01-01T00:00:00.000", "triage": t} for a, b, t in filas])
