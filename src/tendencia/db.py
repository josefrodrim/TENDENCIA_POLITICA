"""
Capa de persistencia SQLite.
Crea el schema, inserta filas y exporta a CSV.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable

from tendencia.schema import Titular

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "titulares.db"

DDL = """
CREATE TABLE IF NOT EXISTS titulares (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    diario            TEXT    NOT NULL,
    fecha             TEXT    NOT NULL,          -- YYYY-MM-DD
    hora_captura      TEXT    NOT NULL DEFAULT '07:00',
    seccion           TEXT    NOT NULL DEFAULT '',
    es_opinion        INTEGER NOT NULL DEFAULT 0, -- 0=False, 1=True
    titular           TEXT    NOT NULL,
    bajada            TEXT    NOT NULL DEFAULT '',
    posicion          INTEGER NOT NULL DEFAULT 99,
    tiene_foto        INTEGER NOT NULL DEFAULT 0,
    candidato         TEXT    NOT NULL DEFAULT 'ninguno',
    url               TEXT    NOT NULL DEFAULT '',
    -- Capa LLM
    valencia_sugerida INTEGER,                   -- -1 | 0 | 1 | NULL
    justificacion_llm TEXT    NOT NULL DEFAULT '',
    -- Codificación humana
    valencia_humana   INTEGER,                   -- -1 | 0 | 1 | NULL
    foto_tono         TEXT    NOT NULL DEFAULT '',
    -- Control de duplicados
    UNIQUE(diario, fecha, titular, candidato)
);

CREATE INDEX IF NOT EXISTS idx_fecha    ON titulares(fecha);
CREATE INDEX IF NOT EXISTS idx_diario   ON titulares(diario);
CREATE INDEX IF NOT EXISTS idx_candidato ON titulares(candidato);
"""

COLUMNS: list[str] = [
    "diario", "fecha", "hora_captura", "seccion", "es_opinion",
    "titular", "bajada", "posicion", "tiene_foto", "candidato", "url",
    "valencia_sugerida", "justificacion_llm", "valencia_humana", "foto_tono",
]


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.executescript(DDL)


def insertar_filas(filas: Iterable[Titular], db_path: Path = DB_PATH) -> int:
    """
    Inserta filas en la BD. Ignora duplicados (ON CONFLICT IGNORE).
    Devuelve el número de filas insertadas.
    """
    sql = f"""
        INSERT OR IGNORE INTO titulares ({', '.join(COLUMNS)})
        VALUES ({', '.join(':' + c for c in COLUMNS)})
    """
    with get_conn(db_path) as conn:
        antes = conn.execute("SELECT COUNT(*) FROM titulares").fetchone()[0]
        conn.executemany(sql, [_normalizar(f) for f in filas])
        despues = conn.execute("SELECT COUNT(*) FROM titulares").fetchone()[0]
    return despues - antes


def exportar_csv(destino: Path, db_path: Path = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM titulares ORDER BY fecha, diario"
        ).fetchall()
    with open(destino, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])


def _normalizar(f: Titular) -> dict:
    d = dict(f)
    d["es_opinion"] = int(bool(d.get("es_opinion", False)))
    d["tiene_foto"] = int(bool(d.get("tiene_foto", False)))
    d.setdefault("valencia_sugerida", None)
    d.setdefault("justificacion_llm", "")
    d.setdefault("valencia_humana", None)
    d.setdefault("foto_tono", "")
    return d
