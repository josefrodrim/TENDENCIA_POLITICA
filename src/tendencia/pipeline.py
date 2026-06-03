"""
Orquestador: fetch → detectar_candidato → insertar en DB.
Agrega scrapers activos en SCRAPERS conforme se van implementando.
"""
from __future__ import annotations

import importlib
from datetime import date, timedelta

from tendencia.config import (
    CANDIDATO_A, CANDIDATO_B, DB_PATH,
    FECHA_FIN, FECHA_INICIO,
    TERMINOS_A, TERMINOS_B,
)
from tendencia.db import init_db, insertar_filas
from tendencia.detection import detectar_candidato
from tendencia.schema import Titular

# Agregar scrapers aquí conforme se implementen
SCRAPERS: dict[str, str] = {
    # ── Plataforma GLR ──────────────────────────────────────────────
    'La República': 'tendencia.scrapers.larepublica',
    'El Popular':   'tendencia.scrapers.elpopular',
    # ── Plataforma Arc / GEC ────────────────────────────────────────
    'El Comercio':  'tendencia.scrapers.elcomercio',
    'Gestión':      'tendencia.scrapers.gestion',
    'Correo':       'tendencia.scrapers.correo',
    'Ojo':          'tendencia.scrapers.ojo',
    # ── HTML scraping ────────────────────────────────────────────────
    'Diario Uno': 'tendencia.scrapers.diariouno',
    'Expreso':    'tendencia.scrapers.expreso',
    'La Razón':   'tendencia.scrapers.larazon',
}


def correr_fecha(fecha: str, verbose: bool = True) -> dict[str, dict]:
    """
    Corre todos los scrapers activos para una fecha y persiste en DB.
    Devuelve resumen por diario: {raw, insertadas} o {error}.
    """
    init_db(DB_PATH)
    resumen: dict[str, dict] = {}

    for diario, modulo_path in SCRAPERS.items():
        mod = importlib.import_module(modulo_path)
        try:
            filas_raw: list[Titular] = mod.fetch(fecha)
        except Exception as e:
            if verbose:
                print(f"  ✗ {diario}: {e}")
            resumen[diario] = {'error': str(e)}
            continue

        filas_final: list[Titular] = []
        for fila in filas_raw:
            filas_final.extend(
                detectar_candidato(fila, TERMINOS_A, TERMINOS_B, CANDIDATO_A, CANDIDATO_B)
            )

        insertadas = insertar_filas(filas_final, db_path=DB_PATH)
        if verbose:
            print(f"  ✓ {diario}: {len(filas_raw)} artículos → {insertadas} insertados")
        resumen[diario] = {'raw': len(filas_raw), 'insertadas': insertadas}

    return resumen


def correr_rango(
    fecha_inicio: str | None = None,
    fecha_fin:    str | None = None,
) -> None:
    """Itera día a día entre fecha_inicio y fecha_fin inclusive."""
    f_ini = date.fromisoformat(fecha_inicio or FECHA_INICIO)
    f_fin = date.fromisoformat(fecha_fin    or FECHA_FIN)

    if not f_ini or not f_fin:
        raise ValueError("Define FECHA_INICIO y FECHA_FIN en .env antes de correr el rango.")

    current = f_ini
    while current <= f_fin:
        fecha_str = current.isoformat()
        print(f"\n── {fecha_str} ──")
        correr_fecha(fecha_str)
        current += timedelta(days=1)
