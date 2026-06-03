"""Tests del flujo exportar → codificar → importar (sin LLM)."""
import csv
import tempfile
from pathlib import Path

import pytest

from tendencia.db import actualizar_humano, exportar_csv, init_db, insertar_filas
from tendencia.schema import fila_vacia


def _fila(diario, titular, candidato, fecha='2026-06-02'):
    f = fila_vacia(diario, fecha)
    f.update({'titular': titular, 'candidato': candidato, 'bajada': 'bajada test'})
    return f


@pytest.fixture
def db_con_datos(tmp_path):
    db = tmp_path / 'test.db'
    init_db(db)
    insertar_filas([
        _fila('La República', 'Keiko lidera encuestas', 'Keiko Fujimori'),
        _fila('La República', 'Sánchez propone reforma', 'Roberto Sanchez'),
        _fila('El Comercio',  'Debate presidencial hoy', 'Keiko Fujimori'),
    ], db_path=db)
    return db


def test_actualizar_humano(db_con_datos):
    filas = [
        {'diario': 'La República', 'fecha': '2026-06-02',
         'titular': 'Keiko lidera encuestas', 'candidato': 'Keiko Fujimori',
         'valencia_humana': '-1', 'foto_tono': 'neutra'},
        {'diario': 'La República', 'fecha': '2026-06-02',
         'titular': 'Sánchez propone reforma', 'candidato': 'Roberto Sanchez',
         'valencia_humana': '1', 'foto_tono': 'favorable'},
    ]
    n = actualizar_humano(filas, db_path=db_con_datos)
    assert n == 2


def test_ignora_filas_sin_valencia(db_con_datos):
    filas = [
        {'diario': 'La República', 'fecha': '2026-06-02',
         'titular': 'Keiko lidera encuestas', 'candidato': 'Keiko Fujimori',
         'valencia_humana': '', 'foto_tono': ''},
    ]
    n = actualizar_humano(filas, db_path=db_con_datos)
    assert n == 0


def test_flujo_completo_exportar_importar(db_con_datos, tmp_path):
    """Simula: exportar → editar CSV → importar → verificar en BD."""
    import sqlite3

    # 1. Exportar
    csv_path = tmp_path / 'titulares.csv'
    exportar_csv(csv_path, db_path=db_con_datos)

    # 2. "Editar" el CSV añadiendo valencia_humana
    with open(csv_path, newline='', encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    for fila in filas:
        if fila['candidato'] != 'ninguno':
            fila['valencia_humana'] = '0'
            fila['foto_tono'] = 'neutra'

    editado = tmp_path / 'titulares_codificado.csv'
    with open(editado, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)

    # 3. Importar
    with open(editado, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    n = actualizar_humano(rows, db_path=db_con_datos)
    assert n == 3

    # 4. Verificar en BD
    conn = sqlite3.connect(db_con_datos)
    codificadas = conn.execute(
        "SELECT COUNT(*) FROM titulares WHERE valencia_humana IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    assert codificadas == 3
