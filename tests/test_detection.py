"""Tests de detección de candidatos por reglas léxicas."""
import pytest

from tendencia.detection import detectar_candidato
from tendencia.schema import fila_vacia

TERMINOS_A = ["García", "Pedro García", "Perú Libre"]
TERMINOS_B = ["Fujimori", "Keiko", "Fuerza Popular"]
LABEL_A = "CandidatoA"
LABEL_B = "CandidatoB"


def _detectar(titular, bajada=""):
    fila = fila_vacia("Test", "2025-06-10")
    fila["titular"] = titular
    fila["bajada"] = bajada
    return detectar_candidato(fila, TERMINOS_A, TERMINOS_B, LABEL_A, LABEL_B)


def test_detecta_candidato_a():
    result = _detectar("García promete reducir pobreza")
    assert len(result) == 1
    assert result[0]["candidato"] == LABEL_A


def test_detecta_candidato_b():
    result = _detectar("Fujimori presenta plan económico")
    assert len(result) == 1
    assert result[0]["candidato"] == LABEL_B


def test_detecta_ambos_duplica():
    result = _detectar("García y Fujimori debaten hoy")
    assert len(result) == 2
    candidatos = {r["candidato"] for r in result}
    assert candidatos == {LABEL_A, LABEL_B}


def test_ninguno():
    result = _detectar("Precio del dólar sube en bolsa")
    assert len(result) == 1
    assert result[0]["candidato"] == "ninguno"


def test_detecta_en_bajada():
    result = _detectar("Encuesta de hoy", bajada="Keiko encabeza preferencias")
    assert result[0]["candidato"] == LABEL_B


def test_case_insensitive():
    result = _detectar("FUJIMORI habla ante el Congreso")
    assert result[0]["candidato"] == LABEL_B
