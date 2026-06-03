"""
Parámetros de la investigación. Define aquí los valores antes de correr el pipeline.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── Definir antes de correr ────────────────────────────────────────────────────
FECHA_INICIO: str = os.getenv("FECHA_INICIO", "")   # "YYYY-MM-DD"
FECHA_FIN: str    = os.getenv("FECHA_FIN",    "")   # "YYYY-MM-DD"

CANDIDATO_A: str = os.getenv("CANDIDATO_A", "")     # etiqueta en la BD
CANDIDATO_B: str = os.getenv("CANDIDATO_B", "")

# Términos para detección por reglas (separados por coma en .env)
_split = lambda v: [t.strip() for t in v.split(",") if t.strip()]
TERMINOS_A: list[str] = _split(os.getenv("TERMINOS_A", CANDIDATO_A))
TERMINOS_B: list[str] = _split(os.getenv("TERMINOS_B", CANDIDATO_B))

# ── LLM ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "titulares.db"
REPORTS_DIR = ROOT / "reports" / "output"
