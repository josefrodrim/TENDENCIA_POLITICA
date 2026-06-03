"""
Detección de candidatos en titular y bajada por reglas léxicas.
Los términos concretos se configuran en config.py (o .env) antes de correr.
"""
from __future__ import annotations

import re

from tendencia.schema import Titular


def _patron(terminos: list[str]) -> re.Pattern:
    escaped = [re.escape(t) for t in sorted(terminos, key=len, reverse=True)]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


def detectar_candidato(
    fila: Titular,
    terminos_a: list[str],
    terminos_b: list[str],
    label_a: str,
    label_b: str,
) -> list[Titular]:
    """
    Analiza titular + bajada y devuelve:
    - [fila con candidato=label_a]        si solo aparece A
    - [fila con candidato=label_b]        si solo aparece B
    - [fila_a, fila_b]                    si aparecen ambos (filas duplicadas)
    - [fila con candidato="ninguno"]      si no aparece ninguno

    terminos_a / terminos_b: listas de strings (nombre, apellido, partido, alias)
    """
    patron_a = _patron(terminos_a)
    patron_b = _patron(terminos_b)
    texto = f"{fila['titular']} {fila['bajada']}"

    menciona_a = bool(patron_a.search(texto))
    menciona_b = bool(patron_b.search(texto))

    if menciona_a and menciona_b:
        fila_a = dict(fila) | {"candidato": label_a}
        fila_b = dict(fila) | {"candidato": label_b}
        return [fila_a, fila_b]  # type: ignore[return-value]
    elif menciona_a:
        return [dict(fila) | {"candidato": label_a}]  # type: ignore[return-value]
    elif menciona_b:
        return [dict(fila) | {"candidato": label_b}]  # type: ignore[return-value]
    else:
        return [dict(fila) | {"candidato": "ninguno"}]  # type: ignore[return-value]
