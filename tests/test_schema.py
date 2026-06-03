"""Tests del esquema de datos y la capa de persistencia."""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from tendencia.db import exportar_csv, init_db, insertar_filas
from tendencia.schema import Titular, fila_vacia


def fila_test(**overrides) -> Titular:
    base = fila_vacia("LaRepublica", "2025-06-10", url="https://larepublica.pe/test")
    base.update(
        titular="Candidato A lidera encuestas",
        bajada="Según última encuesta de Ipsos.",
        posicion=1,
        tiene_foto=True,
        candidato="CandidatoA",
    )
    base.update(overrides)
    return base


@pytest.fixture
def tmp_db(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    return db


def test_init_crea_tabla(tmp_db):
    conn = sqlite3.connect(tmp_db)
    tablas = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    nombres = [t[0] for t in tablas]
    assert "titulares" in nombres


def test_insertar_y_recuperar(tmp_db):
    fila = fila_test()
    insertadas = insertar_filas([fila], db_path=tmp_db)
    assert insertadas == 1

    conn = sqlite3.connect(tmp_db)
    row = conn.execute("SELECT * FROM titulares LIMIT 1").fetchone()
    assert row is not None


def test_duplicado_ignorado(tmp_db):
    fila = fila_test()
    insertar_filas([fila], db_path=tmp_db)
    segunda = insertar_filas([fila], db_path=tmp_db)
    assert segunda == 0


def test_exportar_csv(tmp_db, tmp_path):
    insertar_filas([fila_test()], db_path=tmp_db)
    csv_out = tmp_path / "out.csv"
    exportar_csv(csv_out, db_path=tmp_db)
    contenido = csv_out.read_text()
    assert "titular" in contenido          # cabecera presente
    assert "Candidato A lidera" in contenido


def test_fila_vacia_tiene_todos_los_campos():
    fila = fila_vacia("Gestion", "2025-06-10")
    campos_requeridos = [
        "diario", "fecha", "hora_captura", "seccion", "es_opinion",
        "titular", "bajada", "posicion", "tiene_foto", "candidato", "url",
        "valencia_sugerida", "justificacion_llm", "valencia_humana", "foto_tono",
    ]
    for campo in campos_requeridos:
        assert campo in fila, f"Campo faltante: {campo}"
