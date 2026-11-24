# Protocolo de la prueba de usabilidad

Esto es lo que vamos a hacer con cada persona. Lo escribimos antes de probar para no ajustar la prueba a los resultados.

## Qué queremos saber
1. ¿Una persona que no vio el proyecto logra las cinco tareas sin ayuda?
2. ¿Cuánto tarda?
3. ¿Qué tan fácil le parece? (cuestionario SUS, 10 preguntas)
4. ¿Qué cambiaría?

## A quién
Cinco personas como mínimo (con cinco personas se encuentra cerca del 85 % de los problemas de usabilidad, según Nielsen). Idealmente:
- 2 o más personas que trabajen en salud o en administración de un hospital (rol "coordinador").
- 2 o más personas sin relación con el proyecto que hayan ido a urgencias alguna vez (rol "paciente").

Nadie del equipo ni quien nos ayudó a construir la página cuenta como participante.

## Cómo se hace (unos 10 minutos por persona)
1. Se le explica en una frase qué es la página y se le dice que **se está probando la página, no a la persona**.
2. Se le pide su permiso para anotar el tiempo y sus respuestas, de forma anónima.
3. Se abre la sección "Diseño y pruebas con personas" y se le pide que haga las cinco tareas en voz alta, sin ayuda. Quien observa **no explica ni señala**; solo anota dónde se detiene o se confunde.
4. Cuando termine, responde el cuestionario en la misma página y escribe qué cambiaría.
5. Quien observa anota aparte los puntos de fricción (con hora o tarea) en la hoja de observación de abajo.

### Tareas
| # | Tarea | Éxito si… |
|---|---|---|
| 1 | Elegir el Hospital Local Civil y un día | Lo hace sin ayuda |
| 2 | Encontrar cuántos pacientes se pronosticaron y cuántos llegaron | Dice las dos cifras |
| 3 | Subir la dotación hasta que ninguna hora quede en rojo, o decir que no se puede | Llega a una conclusión correcta |
| 4 | En el asistente, escribir "tengo gripa" y decir cuál centro tiene menos espera | Nombra el centro de la lista |
| 5 | Escribir "me duele el pecho" y decir qué recomienda | Dice que debe ir a urgencias o llamar al 123 |

## Qué se registra (todo anónimo)
Rol, rango de edad (opcional), tareas logradas de 5, segundos, las 10 respuestas SUS y un comentario. La página lo guarda en la tabla `usabilidad_sesion` y `usabilidad_sus`. No se guarda nombre ni correo.

## Cómo se analiza
```
python scripts/analizar_usabilidad.py
```
Calcula el puntaje SUS de cada persona, el promedio con su intervalo de confianza del 95 %, el porcentaje de tareas logradas y el tiempo mediano. Referencias: 68 es el promedio de la industria; más de 80 se considera muy bueno.

## Hoja de observación (una por persona)
| Tarea | ¿Se detuvo o se confundió? | Qué dijo o hizo | Gravedad (1 leve – 3 bloquea) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

## Después de la prueba
Con cada hallazgo grave (2 o 3) hacemos un cambio concreto y lo anotamos en `docs/usabilidad/iteraciones.md`, con la fecha, qué vimos, qué cambiamos y cómo lo comprobamos. Una prueba sin cambios después no sirve de mucho.

## Qué no vamos a hacer
No vamos a inventar resultados, repetir participantes para llegar a cinco ni descartar a quien dé una mala nota. Si el SUS sale bajo, lo publicamos así.
