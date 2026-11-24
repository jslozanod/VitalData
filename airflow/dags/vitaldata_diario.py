"""Flujo diario de VitalData: lee la fuente, carga lo nuevo, controla la calidad, reentrena, evalua y publica.

verificar_fuente -> [cargar_triage, cargar_clima] -> controles_de_calidad -> entrenar_y_publicar -> compuerta_del_modelo -> exportar_snapshot

Las tareas corren en un entorno virtual propio (/home/airflow/vd-venv) porque Airflow 2.10 usa SQLAlchemy 1.4 y
nuestro codigo SQLAlchemy 2. Cada funcion de abajo solo importa y llama a vitaldata.etl.tareas.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import ExternalPythonOperator

PY = "/home/airflow/vd-venv/bin/python"


def t_verificar():
    import sys
    sys.path.insert(0, "/opt/airflow/src")
    from vitaldata.etl import tareas
    return tareas.verificar_fuente()


def t_triage():
    import sys
    sys.path.insert(0, "/opt/airflow/src")
    from vitaldata.etl import tareas
    return tareas.triage_incremental()


def t_clima():
    import sys
    sys.path.insert(0, "/opt/airflow/src")
    from vitaldata.etl import tareas
    return tareas.clima_reciente()


def t_controles():
    import sys
    sys.path.insert(0, "/opt/airflow/src")
    from vitaldata.etl import tareas
    return tareas.controles_de_calidad()


def t_publicar():
    import sys
    sys.path.insert(0, "/opt/airflow/src")
    from vitaldata.etl import tareas
    return tareas.publicar()


def t_compuerta():
    import sys
    sys.path.insert(0, "/opt/airflow/src")
    from vitaldata.etl import tareas
    return tareas.compuerta_del_modelo()


def t_exportar():
    import sys
    sys.path.insert(0, "/opt/airflow/src")
    from vitaldata.etl import tareas
    return tareas.exportar_snapshot()


args = {
    "owner": "equipo-vitaldata",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
}

with DAG(
    dag_id="vitaldata_diario",
    description="ETL de urgencias y clima, controles de calidad, reentrenamiento y publicacion de modelos",
    start_date=datetime(2026, 11, 1),
    schedule="0 5 * * *",           # todos los dias a las 5:00
    catchup=False,
    max_active_runs=1,
    default_args=args,
    tags=["vitaldata", "etl", "modelo"],
    doc_md=__doc__,
) as dag:
    def tarea(task_id, fn, **kw):
        return ExternalPythonOperator(task_id=task_id, python=PY, python_callable=fn, expect_airflow=False, **kw)

    verificar = tarea("verificar_fuente", t_verificar)
    triage = tarea("cargar_triage", t_triage)
    clima = tarea("cargar_clima", t_clima)
    controles = tarea("controles_de_calidad", t_controles)
    entrenar = tarea("entrenar_y_publicar", t_publicar, execution_timeout=timedelta(minutes=40))
    compuerta = tarea("compuerta_del_modelo", t_compuerta)
    exportar = tarea("exportar_snapshot", t_exportar)

    verificar >> [triage, clima] >> controles >> entrenar >> compuerta >> exportar
