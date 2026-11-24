"""Modelos de entrada y salida de la API. Los limites de cada campo son la primera linea de validacion."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class EscenarioIn(BaseModel):
    ips: str = Field(min_length=3, max_length=80)
    fecha: dt.date
    lluvia_mm: float | None = Field(default=None, ge=0, le=200, description="Lluvia del dia en mm; vacio = dato real")
    temp_media: float | None = Field(default=None, ge=-5, le=40, description="Temperatura media del dia en C; vacio = dato real")
    factor_nivel: float = Field(default=1.0, ge=0.3, le=3.0, description="Multiplica el nivel reciente (por ejemplo 1.3 = 30 % mas demanda)")


class OrientarIn(BaseModel):
    texto: str = Field(min_length=1, max_length=400)
    hora: int = Field(ge=0, le=23)
    tipo_dia: Literal["laboral", "sabado", "domingo"] = "laboral"
    dia_semana: int | None = Field(default=None, ge=0, le=6, description="0 = lunes ... 6 = domingo; si se envia, reemplaza al tipo de dia")
    contexto: str | None = Field(default=None, max_length=40, description="Tema de la conversacion (id), para responder preguntas de seguimiento")

    @field_validator("texto")
    @classmethod
    def sin_espacios(cls, v: str) -> str:
        return v.strip()


class UsabilidadIn(BaseModel):
    rol: Literal["coordinador", "paciente", "otro"]
    edad_rango: str | None = Field(default=None, max_length=20)
    experiencia: str | None = Field(default=None, max_length=40)
    tareas_ok: int = Field(ge=0, le=10)
    tareas_total: int = Field(ge=1, le=10)
    segundos: int = Field(ge=0, le=7200)
    comentario: str | None = Field(default=None, max_length=600)
    sus: list[int] = Field(min_length=10, max_length=10, description="Respuestas 1 a 5 del cuestionario SUS, en orden")

    @field_validator("sus")
    @classmethod
    def sus_rango(cls, v: list[int]) -> list[int]:
        if any(x < 1 or x > 5 for x in v):
            raise ValueError("Cada respuesta SUS debe estar entre 1 y 5")
        return v

    @model_validator(mode="after")
    def ok_no_mayor(self):
        if self.tareas_ok > self.tareas_total:
            raise ValueError("tareas_ok no puede ser mayor que tareas_total")
        return self


class UsabilidadOut(BaseModel):
    sesion_id: uuid.UUID
    sus_puntaje: float


class CitaIn(BaseModel):
    ips: str = Field(min_length=2, max_length=80)
    fecha: dt.date
    hora: str = Field(pattern=r"^\d{2}:\d{2}$")
    especialidad: str = Field(min_length=3, max_length=40)
    motivo: str | None = Field(default=None, max_length=300)
    nombre: str = Field(min_length=2, max_length=80)
    contacto: str = Field(min_length=7, max_length=80, description="Correo o celular")
    acepta_datos: bool = Field(description="La persona acepta el tratamiento de sus datos para gestionar la cita")

    @field_validator("acepta_datos")
    @classmethod
    def debe_aceptar(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Debes aceptar el tratamiento de tus datos para reservar")
        return v


class ResenaIn(BaseModel):
    estrellas: int = Field(ge=1, le=5)
    nombre: str | None = Field(default=None, max_length=40)
    comentario: str = Field(min_length=5, max_length=500)


class SolicitudDemoIn(BaseModel):
    institucion: str = Field(min_length=2, max_length=120)
    nombre: str = Field(min_length=2, max_length=80)
    cargo: str | None = Field(default=None, max_length=60)
    contacto: str = Field(min_length=7, max_length=80, description="Correo o celular")
    mensaje: str | None = Field(default=None, max_length=500)
    acepta_datos: bool

    @field_validator("acepta_datos")
    @classmethod
    def debe_aceptar(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Debes aceptar el tratamiento de tus datos para que podamos contactarte")
        return v
