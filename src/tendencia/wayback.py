"""
Recuperación histórica via Wayback Machine (Internet Archive).

Para fechas que ya no están en los RSS actuales (generalmente > 5-7 días atrás),
busca el snapshot más cercano a las 07:00 hora Perú (= 12:00 UTC) y pasa el
contenido archivado directamente a los parsers existentes.

Los parsers (parse_glr_rss, parse_arc_rss, parse_larazon, parse_expreso) no
hacen peticiones HTTP — solo reciben texto y una fecha, por lo que funcionan
igual con contenido en vivo o archivado.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

import requests

from tendencia.config import (
    CANDIDATO_A, CANDIDATO_B, DB_PATH,
    TERMINOS_A, TERMINOS_B,
)
from tendencia.db import init_db, insertar_filas
from tendencia.detection import detectar_candidato
from tendencia.scrapers.arc_base import parse_arc_rss
from tendencia.scrapers.expreso import parse_expreso
from tendencia.scrapers.glr_base import parse_glr_rss
from tendencia.scrapers.larazon import parse_larazon
from tendencia.schema import Titular

# ── Registro de fuentes ──────────────────────────────────────────────────────
# (diario, url_original, tipo_parser)
# Mismo orden que el pipeline activo.
FUENTES: list[tuple[str, str, str]] = [
    ('La República', 'https://larepublica.pe/rss/home.xml',                      'glr'),
    ('La República', 'https://larepublica.pe/rss/politica.xml',                  'glr'),
    ('El Popular',   'https://www.elpopular.pe/rss/home.xml',                    'glr'),
    ('El Comercio',  'https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml', 'arc'),
    ('Gestión',      'https://gestion.pe/arc/outboundfeeds/rss/?outputType=xml',    'arc'),
    ('Correo',       'https://diariocorreo.pe/arc/outboundfeeds/rss/?outputType=xml','arc'),
    ('Ojo',          'https://ojo.pe/arc/outboundfeeds/rss/?outputType=xml',        'arc'),
    ('La Razón',     'https://larazon.pe/',                                         'larazon'),
]

_CDX   = 'http://web.archive.org/cdx/search/cdx'
_WB    = 'https://web.archive.org/web'
_UA    = 'TendenciaPoliticaBot/0.1 (investigacion academica; josef.rodrim@gmail.com)'
_SESS  = requests.Session()
_SESS.headers.update({'User-Agent': _UA})

# Máxima distancia aceptable entre el snapshot y la hora objetivo (segundos)
_MAX_DELTA_S = 18 * 3600  # 18 horas


def _timestamp_objetivo(fecha: str) -> str:
    """
    07:00 hora Perú (UTC-5) = 12:00 UTC  →  'YYYYMMDD120000'
    """
    return fecha.replace('-', '') + '120000'


def buscar_snapshot(url: str, fecha: str) -> str | None:
    """
    Consulta la CDX API y devuelve la URL de Wayback del snapshot más cercano
    a las 07:00 Perú en 'fecha'.  Devuelve None si no hay snapshot en rango.
    """
    ts = _timestamp_objetivo(fecha)
    try:
        resp = _SESS.get(_CDX, params={
            'url':     url,
            'output':  'json',
            'limit':   '1',
            'closest': ts,
            'fl':      'timestamp,statuscode',
            'filter':  'statuscode:200',
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"    CDX error [{url}]: {e}")
        return None

    if not data or len(data) < 2:   # data[0] = cabecera
        return None

    snap_ts = data[1][0]            # primer resultado, campo timestamp

    # Verificar que el snapshot no está demasiado lejos de la hora objetivo
    delta = abs(int(snap_ts) - int(ts))
    if delta > int(_MAX_DELTA_S / 60 * 100):   # aprox en unidades YYYYMMDDHHMMSS
        return None

    return f"{_WB}/{snap_ts}/{url}"


def _fetch_wayback(wb_url: str) -> str | None:
    """Descarga el contenido archivado de Wayback. Delay 2-3s para no sobrecargar."""
    time.sleep(2.5)
    try:
        resp = _SESS.get(wb_url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"    Fetch error [{wb_url[:70]}]: {e}")
        return None


def _parsear(contenido: str, diario: str, tipo: str, fecha: str) -> list[Titular]:
    if tipo == 'glr':
        return parse_glr_rss(contenido, diario, fecha)
    elif tipo == 'arc':
        return parse_arc_rss(contenido, diario, fecha)
    elif tipo == 'larazon':
        return parse_larazon(contenido, fecha)
    elif tipo == 'expreso':
        return parse_expreso(contenido, fecha)
    return []


def recuperar_fecha(fecha: str, verbose: bool = True) -> dict[str, int]:
    """
    Recupera artículos de una fecha histórica usando Wayback Machine.
    Devuelve resumen {diario: filas_insertadas}.
    """
    init_db(DB_PATH)
    resumen: dict[str, int] = {}
    vistas_diario: dict[str, set[str]] = {}

    for diario, url_orig, tipo in FUENTES:
        if verbose:
            print(f"  [{diario}] {url_orig.split('/')[2]}…", end=' ', flush=True)

        wb_url = buscar_snapshot(url_orig, fecha)
        if not wb_url:
            if verbose:
                print('sin snapshot')
            continue

        contenido = _fetch_wayback(wb_url)
        if not contenido:
            continue

        filas_raw = _parsear(contenido, diario, tipo, fecha)
        if not filas_raw:
            if verbose:
                print('0 artículos en esa fecha')
            continue

        # Deduplicar entre feeds del mismo diario (e.g. home + politica)
        if diario not in vistas_diario:
            vistas_diario[diario] = set()
        filas_unicas = [f for f in filas_raw if f['url'] not in vistas_diario[diario]]
        for f in filas_unicas:
            vistas_diario[diario].add(f['url'])

        # Detección de candidato
        filas_final: list[Titular] = []
        for fila in filas_unicas:
            filas_final.extend(
                detectar_candidato(fila, TERMINOS_A, TERMINOS_B, CANDIDATO_A, CANDIDATO_B)
            )

        insertadas = insertar_filas(filas_final, db_path=DB_PATH)
        resumen[diario] = resumen.get(diario, 0) + insertadas
        if verbose:
            print(f'{len(filas_raw)} artículos → {insertadas} insertadas')

    return resumen


def recuperar_rango(
    fecha_inicio: str,
    fecha_fin:    str,
    verbose: bool = True,
) -> None:
    """Itera día a día y recupera histórico de cada fecha."""
    f_ini = date.fromisoformat(fecha_inicio)
    f_fin = date.fromisoformat(fecha_fin)
    current = f_ini
    while current <= f_fin:
        fecha_str = current.isoformat()
        print(f"\n── {fecha_str} (Wayback) ──")
        recuperar_fecha(fecha_str, verbose=verbose)
        current += timedelta(days=1)
        time.sleep(1)   # pausa entre días para no saturar la API
