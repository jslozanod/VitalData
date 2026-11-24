-- Esquema de VitalData (PostgreSQL 16)
-- Modelo en estrella: dimensiones pequenas + una tabla de hechos con cada atencion de urgencias.
-- Todo se puede volver a ejecutar sin romper nada (IF NOT EXISTS).

CREATE SCHEMA IF NOT EXISTS vd;
SET search_path TO vd, public;

-- ---------- dimensiones ----------
CREATE TABLE IF NOT EXISTS dim_ips (
    ips_id      SMALLSERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL UNIQUE,
    red         TEXT,
    entidad     TEXT
);

CREATE TABLE IF NOT EXISTS dim_triage (
    triage_id   SMALLINT PRIMARY KEY CHECK (triage_id BETWEEN 1 AND 5),
    nivel       TEXT NOT NULL UNIQUE,
    descripcion TEXT NOT NULL
);
INSERT INTO dim_triage (triage_id, nivel, descripcion) VALUES
    (1, 'I',   'Reanimacion: atencion inmediata'),
    (2, 'II',  'Emergencia: muy urgente'),
    (3, 'III', 'Urgencia: urgente'),
    (4, 'IV',  'Urgencia menor: poco urgente'),
    (5, 'V',   'Sin urgencia: no urgente')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS dim_estacion (
    estacion_id TEXT PRIMARY KEY,
    nombre      TEXT NOT NULL,
    municipio   TEXT NOT NULL,
    latitud     DOUBLE PRECISION,
    longitud    DOUBLE PRECISION
);

-- ---------- auditoria del ETL ----------
CREATE TABLE IF NOT EXISTS etl_run (
    etl_run_id          BIGSERIAL PRIMARY KEY,
    flujo               TEXT NOT NULL,
    inicio              TIMESTAMPTZ NOT NULL DEFAULT now(),
    fin                 TIMESTAMPTZ,
    estado              TEXT NOT NULL DEFAULT 'en_curso' CHECK (estado IN ('en_curso','ok','error')),
    filas_extraidas     INTEGER,
    filas_duplicadas    INTEGER,
    filas_rechazadas    INTEGER,
    filas_corregidas    INTEGER,
    filas_cargadas      INTEGER,
    detalle             JSONB
);

CREATE TABLE IF NOT EXISTS dq_issue (
    issue_id    BIGSERIAL PRIMARY KEY,
    etl_run_id  BIGINT NOT NULL REFERENCES etl_run(etl_run_id) ON DELETE CASCADE,
    regla       TEXT NOT NULL,
    severidad   TEXT NOT NULL CHECK (severidad IN ('info','aviso','error')),
    filas       INTEGER NOT NULL,
    accion      TEXT NOT NULL,
    ejemplo     JSONB
);

-- ---------- hechos ----------
CREATE TABLE IF NOT EXISTS fact_atencion (
    atencion_id BIGSERIAL PRIMARY KEY,
    ips_id      SMALLINT NOT NULL REFERENCES dim_ips(ips_id),
    triage_id   SMALLINT NOT NULL REFERENCES dim_triage(triage_id),
    ingreso     TIMESTAMP NOT NULL,
    atencion    TIMESTAMP NOT NULL,
    espera_min  REAL NOT NULL,
    huella      CHAR(32) NOT NULL UNIQUE,      -- md5 de la fila cruda: hace la carga idempotente
    etl_run_id  BIGINT REFERENCES etl_run(etl_run_id),
    CONSTRAINT atencion_despues_de_ingreso CHECK (atencion >= ingreso),
    CONSTRAINT espera_razonable CHECK (espera_min >= 0 AND espera_min <= 1440)
);
CREATE INDEX IF NOT EXISTS ix_fact_ips_ingreso ON fact_atencion (ips_id, ingreso);

CREATE TABLE IF NOT EXISTS clima_diario (
    estacion_id TEXT NOT NULL REFERENCES dim_estacion(estacion_id),
    fecha       DATE NOT NULL,
    lluvia_mm   REAL,
    temp_media  REAL,
    temp_max    REAL,
    temp_min    REAL,
    n_lluvia    INTEGER,
    n_temp      INTEGER,
    PRIMARY KEY (estacion_id, fecha)
);

-- ---------- agregado por hora (lo que consume el modelo) ----------
CREATE TABLE IF NOT EXISTS agg_llegadas_hora (
    ips_id      SMALLINT NOT NULL REFERENCES dim_ips(ips_id),
    hora        TIMESTAMP NOT NULL,
    llegadas    INTEGER NOT NULL CHECK (llegadas >= 0),
    espera_media REAL,
    espera_p90  REAL,
    PRIMARY KEY (ips_id, hora)
);

-- ---------- modelos ----------
CREATE TABLE IF NOT EXISTS model_run (
    model_run_id BIGSERIAL PRIMARY KEY,
    ips_id       SMALLINT NOT NULL REFERENCES dim_ips(ips_id),
    creado       TIMESTAMPTZ NOT NULL DEFAULT now(),
    algoritmo    TEXT NOT NULL,
    train_desde  TIMESTAMP,
    train_hasta  TIMESTAMP,
    test_desde   TIMESTAMP,
    test_hasta   TIMESTAMP,
    metricas     JSONB NOT NULL,
    parametros   JSONB,
    etl_run_id   BIGINT REFERENCES etl_run(etl_run_id),
    vigente      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS forecast_hora (
    model_run_id BIGINT NOT NULL REFERENCES model_run(model_run_id) ON DELETE CASCADE,
    ips_id       SMALLINT NOT NULL REFERENCES dim_ips(ips_id),
    hora         TIMESTAMP NOT NULL,
    modelo       TEXT NOT NULL,
    prediccion   REAL NOT NULL,
    lo80         REAL,
    hi80         REAL,
    real         INTEGER,
    PRIMARY KEY (model_run_id, modelo, hora)
);

-- ---------- pruebas con usuarios ----------
CREATE TABLE IF NOT EXISTS usabilidad_sesion (
    sesion_id    UUID PRIMARY KEY,
    creada       TIMESTAMPTZ NOT NULL DEFAULT now(),
    rol          TEXT NOT NULL CHECK (rol IN ('coordinador','paciente','otro')),
    edad_rango   TEXT,
    experiencia  TEXT,
    tareas_ok    SMALLINT CHECK (tareas_ok BETWEEN 0 AND 10),
    tareas_total SMALLINT CHECK (tareas_total BETWEEN 1 AND 10),
    segundos     INTEGER CHECK (segundos >= 0),
    comentario   TEXT
);
CREATE TABLE IF NOT EXISTS usabilidad_sus (
    sesion_id    UUID PRIMARY KEY REFERENCES usabilidad_sesion(sesion_id) ON DELETE CASCADE,
    q1 SMALLINT NOT NULL CHECK (q1 BETWEEN 1 AND 5), q2 SMALLINT NOT NULL CHECK (q2 BETWEEN 1 AND 5),
    q3 SMALLINT NOT NULL CHECK (q3 BETWEEN 1 AND 5), q4 SMALLINT NOT NULL CHECK (q4 BETWEEN 1 AND 5),
    q5 SMALLINT NOT NULL CHECK (q5 BETWEEN 1 AND 5), q6 SMALLINT NOT NULL CHECK (q6 BETWEEN 1 AND 5),
    q7 SMALLINT NOT NULL CHECK (q7 BETWEEN 1 AND 5), q8 SMALLINT NOT NULL CHECK (q8 BETWEEN 1 AND 5),
    q9 SMALLINT NOT NULL CHECK (q9 BETWEEN 1 AND 5), q10 SMALLINT NOT NULL CHECK (q10 BETWEEN 1 AND 5)
);


-- ---------- citas y resenas de los pacientes ----------
CREATE TABLE IF NOT EXISTS cita (
    cita_id      BIGSERIAL PRIMARY KEY,
    codigo       TEXT NOT NULL UNIQUE,
    ips_id       SMALLINT NOT NULL REFERENCES dim_ips(ips_id),
    fecha        DATE NOT NULL,
    hora         TIME NOT NULL CHECK (hora BETWEEN TIME '06:00' AND TIME '20:30'),
    cupo         SMALLINT NOT NULL CHECK (cupo BETWEEN 1 AND 10),
    especialidad TEXT NOT NULL,
    motivo       TEXT CHECK (motivo IS NULL OR length(motivo) <= 300),
    nombre       TEXT NOT NULL CHECK (length(nombre) BETWEEN 2 AND 80),
    contacto     TEXT NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'reservada' CHECK (estado IN ('reservada', 'cancelada')),
    creada       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- un cupo de una franja solo lo puede tener una cita reservada: evita que dos personas tomen el mismo cupo
CREATE UNIQUE INDEX IF NOT EXISTS ux_cita_cupo ON cita (ips_id, fecha, hora, cupo) WHERE estado = 'reservada';
CREATE INDEX IF NOT EXISTS ix_cita_ips_fecha ON cita (ips_id, fecha);

CREATE TABLE IF NOT EXISTS resena (
    resena_id  BIGSERIAL PRIMARY KEY,
    estrellas  SMALLINT NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
    nombre     TEXT CHECK (nombre IS NULL OR length(nombre) <= 40),
    comentario TEXT NOT NULL CHECK (length(comentario) BETWEEN 5 AND 500),
    creada     TIMESTAMPTZ NOT NULL DEFAULT now(),
    visible    BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS ix_resena_creada ON resena (creada DESC);


-- ---------- solicitudes de demostracion de hospitales ----------
CREATE TABLE IF NOT EXISTS solicitud_demo (
    solicitud_id BIGSERIAL PRIMARY KEY,
    institucion  TEXT NOT NULL CHECK (length(institucion) BETWEEN 2 AND 120),
    nombre       TEXT NOT NULL CHECK (length(nombre) BETWEEN 2 AND 80),
    cargo        TEXT CHECK (cargo IS NULL OR length(cargo) <= 60),
    contacto     TEXT NOT NULL,
    mensaje      TEXT CHECK (mensaje IS NULL OR length(mensaje) <= 500),
    creada       TIMESTAMPTZ NOT NULL DEFAULT now()
);
