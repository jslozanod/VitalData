"""Modelo de colas M/M/c (formula de Erlang C) para traducir llegadas por hora en personal y espera.

Es una abstraccion de planeacion: supone llegadas aleatorias, atencion de duracion promedio fija y una sola cola.
Los datos reales de Pasto no traen cuanto personal habia en cada turno, asi que aqui el personal se recomienda
a partir de una meta de espera que define quien usa la herramienta, no se calibra con datos."""
from __future__ import annotations

import math


def erlang_c(c: int, a: float) -> float:
    """Probabilidad de que un paciente que llega tenga que esperar. a = llegadas por hora x horas por atencion."""
    if c < 1:
        raise ValueError("c debe ser al menos 1")
    if a < 0:
        raise ValueError("la carga ofrecida no puede ser negativa")
    if a == 0:
        return 0.0
    if a >= c:
        return 1.0
    # suma estable: termino k = a^k / k!
    termino, suma = 1.0, 1.0
    for k in range(1, c):
        termino *= a / k
        suma += termino
    termino *= a / c                      # a^c / c!
    cola = termino * c / (c - a)
    return cola / (suma + cola)


def espera_media_min(llegadas_hora: float, c: int, servicio_min: float) -> float:
    """Espera media en cola (minutos). Si las llegadas superan la capacidad la cola crece sin limite: inf."""
    if llegadas_hora < 0 or servicio_min <= 0:
        raise ValueError("llegadas y servicio deben ser positivos")
    if llegadas_hora == 0:
        return 0.0
    mu = 60.0 / servicio_min                         # atenciones por hora de cada persona
    a = llegadas_hora / mu
    if a >= c:
        return math.inf
    pc = erlang_c(c, a)
    return pc / (c * mu - llegadas_hora) * 60.0


def personal_necesario(llegadas_hora: float, servicio_min: float, meta_min: float, c_max: int = 80) -> int:
    """Menor numero de personas que mantiene la espera media por debajo de la meta."""
    if meta_min < 0:
        raise ValueError("la meta de espera no puede ser negativa")
    if llegadas_hora <= 0:
        return 1
    mu = 60.0 / servicio_min
    c = max(1, math.floor(llegadas_hora / mu) + 1)
    while c <= c_max:
        if espera_media_min(llegadas_hora, c, servicio_min) <= meta_min:
            return c
        c += 1
    return c_max
