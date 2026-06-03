"""
Esquema de datos central. Toda fila del pipeline cumple esta estructura,
sin importar si viene de web scraping o de PDF.
"""
from __future__ import annotations

from typing import Literal, TypedDict


Valencia = Literal[-1, 0, 1]
FotoTono = Literal["favorable", "neutra", "desfavorable", ""]


class Titular(TypedDict):
    # ── Campos de captura ──────────────────────────────────────────────
    diario: str
    fecha: str          # ISO-8601: "YYYY-MM-DD"
    hora_captura: str   # "HH:MM"
    seccion: str
    es_opinion: bool
    titular: str
    bajada: str         # cadena vacía si no hay
    posicion: int       # 1 = titular principal de portada
    tiene_foto: bool
    candidato: str      # CANDIDATO_A | CANDIDATO_B | "ninguno" | "ambos→duplicado"
    url: str

    # ── Capa de codificación (LLM) ─────────────────────────────────────
    valencia_sugerida: int | None   # -1 | 0 | 1 | None (aún no procesado)
    justificacion_llm: str          # cadena vacía si no procesado

    # ── Codificación humana (la llena el investigador) ─────────────────
    valencia_humana: int | None     # -1 | 0 | 1 | None
    foto_tono: FotoTono


def fila_vacia(diario: str, fecha: str, url: str = "") -> Titular:
    """Devuelve una fila con valores por defecto; útil como plantilla en scrapers."""
    return Titular(
        diario=diario,
        fecha=fecha,
        hora_captura="07:00",
        seccion="",
        es_opinion=False,
        titular="",
        bajada="",
        posicion=99,
        tiene_foto=False,
        candidato="ninguno",
        url=url,
        valencia_sugerida=None,
        justificacion_llm="",
        valencia_humana=None,
        foto_tono="",
    )
