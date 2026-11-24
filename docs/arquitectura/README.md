# Arquitectura

Estos diagramas se ven directamente en GitHub (Mermaid). La versión interactiva está en la sección 7 de la página (`web/index.html`).

## Visión general

```mermaid
flowchart LR
  subgraph Fuentes["Datos abiertos (datos.gov.co)"]
    F1["Pasto Salud<br/>triage de urgencias"]
    F2["IDEAM<br/>lluvia y temperatura"]
  end
  subgraph Compose["docker compose"]
    AF["Airflow<br/>DAG vitaldata_diario"]
    ETL["ETL Python<br/>extraer · validar · cargar"]
    DB[("PostgreSQL 16<br/>esquema vd")]
    ML["Modelos<br/>Poisson · backtest · publicar"]
    API["FastAPI<br/>/api/*"]
    WEB["Página web<br/>HTML + JS sin librerías"]
  end
  F1 --> ETL
  F2 --> ETL
  AF -->|orquesta| ETL
  AF -->|orquesta| ML
  ETL --> DB
  DB --> ML
  ML -->|métricas y pronósticos| DB
  DB --> API
  API --> WEB
  AF -->|exporta| SNAP["web/data/snapshot.js<br/>modo sin servidor"]
  SNAP -.-> WEB
  T["pytest<br/>unitarias · integración · límites"] -.-> ETL
  T -.-> API
```

## Flujo diario (Airflow)

```mermaid
flowchart LR
  A[verificar_fuente] --> B[cargar_triage]
  A --> C[cargar_clima]
  B --> D[controles_de_calidad]
  C --> D
  D --> E[entrenar_y_publicar]
  E --> F[compuerta_del_modelo]
  F --> G[exportar_snapshot]
```

Cada tarea reintenta dos veces con espera creciente. `controles_de_calidad` detiene el flujo si la tabla de hechos no coincide con el agregado, si hay una atención anterior a su ingreso o si hay huellas repetidas. `compuerta_del_modelo` detiene la publicación si el modelo no le gana a la mejor referencia en al menos la mitad de los centros.

## Modelo de datos

```mermaid
erDiagram
  dim_ips ||--o{ fact_atencion : "ips_id"
  dim_triage ||--o{ fact_atencion : "triage_id"
  dim_ips ||--o{ agg_llegadas_hora : "ips_id"
  dim_estacion ||--o{ clima_diario : "estacion_id"
  dim_ips ||--o{ model_run : "ips_id"
  model_run ||--o{ forecast_hora : "model_run_id"
  etl_run ||--o{ dq_issue : "etl_run_id"
  etl_run ||--o{ fact_atencion : "etl_run_id"
  usabilidad_sesion ||--|| usabilidad_sus : "sesion_id"

  fact_atencion {
    bigint atencion_id PK
    smallint ips_id FK
    smallint triage_id FK
    timestamp ingreso
    timestamp atencion
    real espera_min
    char huella UK
  }
  agg_llegadas_hora {
    smallint ips_id PK
    timestamp hora PK
    int llegadas
    real espera_media
  }
  clima_diario {
    text estacion_id PK
    date fecha PK
    real lluvia_mm
    real temp_media
  }
  model_run {
    bigint model_run_id PK
    smallint ips_id FK
    jsonb metricas
    bool vigente
  }
```

## Decisiones y por qué

| Decisión | Por qué | Alternativa que descartamos |
|---|---|---|
| Datos reales de Pasto Salud en vez de simulados | Es el mismo tipo de dato que tendría un hospital cliente (ingreso, triage, atención) y cualquiera puede comprobarlo | Seguir con datos simulados: no demuestra nada sobre el mundo real |
| Poisson por hora con perfil por tipo de día | Las llegadas por hora son conteos pequeños; Poisson los modela directo y da rangos | Redes neuronales o Prophet: con 2-3 llegadas por hora no ganan y no se pueden explicar |
| Nivel de la última semana como variable | En mayo de 2022 las llegadas casi se duplicaron; un promedio de toda la historia habría fallado | Reentrenar solo cada mes |
| Validación con ventana que avanza | Es la forma honesta de medir un pronóstico: nunca se entrena con el futuro | Partir los datos al azar (mezcla pasado y futuro) |
| Referencias sin IA obligatorias | Si no las supera, el modelo no sirve | Reportar solo la precisión del modelo |
| Erlang C para el personal | Es el modelo estándar de colas y se explica en una frase | Calibrarlo con los datos: no traen el personal por turno |
| Carga idempotente por huella md5 | Correr el ETL dos veces no duplica | Truncar y recargar siempre |
| Restricciones en la base | Un error de limpieza no puede dejar datos imposibles | Confiar solo en el código |
| Página sin librerías y con modo sin servidor | Funciona sin internet y abierta desde el disco | Un framework de gráficos |
