# Diccionario de datos

## Fuentes (datos abiertos, sin credenciales)

| Fuente | Conjunto | Qué trae | Cobertura |
|---|---|---|---|
| E.S.E. Pasto Salud (Nariño) | `vt5n-eu2r` "Clasificación en Triage Urgencias" en datos.gov.co | Una fila por paciente atendido en urgencias: ingreso, atención, triage, IPS y red | 1 de enero de 2020 a 29 de septiembre de 2022 (con un hueco de abril de 2020 a marzo de 2021) |
| IDEAM | `s54a-sgyg` Precipitación | Lluvia en mm, lectura cada 10 minutos | Estación Universidad de Nariño (0052045080), Pasto |
| IDEAM | `sbwg-7ju4` Temperatura ambiente del aire | Temperatura a 2 m en °C, pocas lecturas por día | Misma estación |

Los enlaces y la fecha de consulta están en el README. Cualquiera puede repetir la descarga con `python scripts/correr_etl.py --triage --clima`.

## Tablas (esquema `vd` en PostgreSQL)

### `fact_atencion` (hechos)
| Columna | Tipo | Significado |
|---|---|---|
| atencion_id | bigserial PK | Identificador |
| ips_id | smallint FK → dim_ips | Centro de salud |
| triage_id | smallint FK → dim_triage | 1 (I, reanimación) a 5 (V, sin urgencia) |
| ingreso | timestamp | Cuándo llegó el paciente |
| atencion | timestamp | Cuándo lo atendieron (la fuente lo trae al minuto) |
| espera_min | real | atención − ingreso, en minutos |
| huella | char(32) único | md5 de la fila cruda: hace la carga idempotente |

Restricciones: `atencion >= ingreso`, `0 <= espera_min <= 1440`, llaves foráneas a las dimensiones.

### `agg_llegadas_hora`
Llegadas por IPS y por hora (`llegadas`) con la espera media y el percentil 90 de esa hora. Es lo que consume el modelo. Las horas sin llegadas no tienen fila; el código las rellena con 0 solo dentro del periodo continuo.

### `clima_diario`
Lluvia (mm) y temperatura (°C) por día y estación. Un día con pocas lecturas queda en `NULL`: menos de 100 lecturas de lluvia o menos de 3 de temperatura.

### `etl_run` y `dq_issue`
Una fila por corrida del ETL (también las que fallan) y una fila por regla de calidad aplicada, con cuántas filas tocó y qué se hizo.

### `model_run` y `forecast_hora`
Una fila por modelo publicado, con sus métricas en JSON, y los pronósticos del periodo de prueba (modelo, hora, predicción, rango del 80 % y lo que ocurrió) para el modelo y las tres referencias.

### `usabilidad_sesion` y `usabilidad_sus`
Una fila por persona que hizo la prueba (anónima) y sus diez respuestas del cuestionario SUS.

## Reglas de limpieza (`src/vitaldata/etl/validate.py`)

| Regla | Qué hace | En la última carga |
|---|---|---|
| `fila_duplicada_exacta` | Deja una sola copia de las filas idénticas (milisegundo incluido) | 9.932 filas |
| `espera_negativa_por_redondeo` | Si la atención quedó hasta un minuto antes del ingreso (la fuente la corta al minuto), espera = 0 | 175 filas |
| `triage_no_valido`, `fecha_no_valida`, `fecha_fuera_de_rango`, `ips_vacia`, `espera_negativa`, `espera_mayor_a_24h` | Rechaza la fila | 0 filas |
| `espera_en_tope_de_360_min` | Solo avisa: la fuente parece cortar la espera en 6 horas | 3 filas |
| `ips_con_pocos_registros` | Se cargan, pero no se modelan (menos de 5.000 atenciones) | 5 centros pequeños |

## Variables del modelo
Perfil por hora del día y tipo de día (laboral, sábado, domingo o festivo), día de la semana, nivel de la última semana (promedio diario de los 7 días anteriores, solo pasado), lluvia del día (log) y temperatura media del día. Los festivos son los de Colombia (paquete `holidays`).
