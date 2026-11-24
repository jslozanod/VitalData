FROM apache/airflow:2.10.5-python3.12
USER airflow
# Airflow 2.10 necesita SQLAlchemy 1.4; nuestro codigo usa SQLAlchemy 2. Por eso las tareas de VitalData corren en un
# entorno virtual aparte (ExternalPythonOperator) con sus propias librerias.
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /home/airflow/vd-venv && /home/airflow/vd-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
