"""
Utilidades compartidas por todos los scrapers.

Contrato de cada scraper:
    def fetch(fecha: str) -> list[Titular]
    - fecha en formato "YYYY-MM-DD"
    - Devuelve lista (puede ser vacía si no hay cobertura)
    - Lanza ScraperError solo ante fallos irrecuperables
"""
from __future__ import annotations

import random
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from tendencia.schema import Titular  # noqa: F401  (reexport para scrapers)

USER_AGENT = (
    "TendenciaPoliticaBot/0.1 "
    "(investigacion academica cobertura electoral Peru; "
    "contacto: josef.rodrim@gmail.com)"
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

_robots_cache: dict[str, RobotFileParser] = {}


class ScraperError(Exception):
    pass


class ExcluidoPorRobots(ScraperError):
    """Se lanza cuando robots.txt prohíbe el acceso."""


def puede_scrapear(url: str) -> bool:
    """Verifica robots.txt. Usa caché por dominio."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception:
            # Si no hay robots.txt accesible, asumimos permitido
            rp.allow_all = True
        _robots_cache[base] = rp
    return _robots_cache[base].can_fetch(USER_AGENT, url)


def get_html(url: str, timeout: int = 20) -> str:
    """
    Descarga HTML de una URL respetando robots.txt.
    Lanza ExcluidoPorRobots si está prohibido.
    Aplica delay aleatorio 3-6 s antes de la petición.
    """
    if not puede_scrapear(url):
        raise ExcluidoPorRobots(f"robots.txt prohíbe: {url}")
    time.sleep(random.uniform(3, 6))
    resp = SESSION.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
