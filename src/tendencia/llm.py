"""
Capa de codificación LLM — propone valencia_sugerida por fila.

IMPORTANTE: Es solo apoyo al codificador humano.
El dato de análisis es valencia_humana (llenado manualmente por el investigador).
No reportar conclusiones basadas en valencia_sugerida sin validación humana.

Usa prompt caching de Anthropic para reducir costo en lotes grandes.
"""
from __future__ import annotations

import json

import anthropic

from tendencia.config import ANTHROPIC_API_KEY, CANDIDATO_A, CANDIDATO_B, DB_PATH, LLM_MODEL
from tendencia.db import get_conn

_SYSTEM = f"""Eres un asistente de investigación académica neutral.
Analizas titulares de diarios peruanos durante la segunda vuelta electoral 2026
entre {CANDIDATO_A} y {CANDIDATO_B}.

Tu tarea: determinar la valencia informativa de un titular hacia el candidato indicado.

DEFINICIONES:
-1 (negativa): lenguaje crítico, asociación con escándalo, señalamiento de error o fallo, \
criminalización, cuestionamiento de idoneidad
 0 (neutra): cobertura informativa y descriptiva, sin juicio de valor implícito
+1 (positiva): logro mencionado, propuesta bien valorada, apoyo recibido, imagen favorable

REGLAS:
- Aplica los MISMOS criterios para ambos candidatos sin excepción
- Si es artículo de opinión, evalúa el tono del argumento hacia el candidato
- Si hay ambigüedad genuina, elige 0
- Responde ÚNICAMENTE con JSON válido, sin texto adicional antes ni después

FORMATO:
{{"valencia": <-1|0|1>, "justificacion": "<máximo 120 caracteres>"}}"""


def _sugerir_una(fila: dict, client: anthropic.Anthropic) -> dict:
    tipo = "artículo de opinión" if fila.get('es_opinion') else "noticia"
    user_msg = (
        f"Candidato evaluado: {fila['candidato']}\n"
        f"Diario: {fila['diario']} | Tipo: {tipo}\n"
        f"Titular: {fila['titular']}\n"
        f"Bajada: {fila.get('bajada', '') or '(sin bajada)'}"
    )
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=200,
        system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_msg}],
    )
    try:
        result = json.loads(response.content[0].text.strip())
        return {
            'valencia_sugerida': int(result['valencia']),
            'justificacion_llm': str(result.get('justificacion', ''))[:200],
        }
    except (json.JSONDecodeError, KeyError, ValueError):
        raw = response.content[0].text.strip()[:100]
        return {'valencia_sugerida': 0, 'justificacion_llm': f'[parse error] {raw}'}


def procesar_pendientes(limite: int | None = None, verbose: bool = True) -> int:
    """
    Procesa filas con candidato != 'ninguno' y valencia_sugerida IS NULL.
    Actualiza la BD. Devuelve número de filas procesadas.
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY no configurada en .env")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    sql = """
        SELECT id, diario, fecha, titular, bajada, candidato, es_opinion
        FROM   titulares
        WHERE  candidato != 'ninguno'
          AND  valencia_sugerida IS NULL
        ORDER  BY fecha, diario
    """
    if limite:
        sql += f" LIMIT {limite}"

    conn = get_conn(DB_PATH)
    filas = [dict(r) for r in conn.execute(sql).fetchall()]
    conn.close()

    procesadas = 0
    for fila in filas:
        resultado = _sugerir_una(fila, client)
        with get_conn(DB_PATH) as c:
            c.execute(
                "UPDATE titulares SET valencia_sugerida=?, justificacion_llm=? WHERE id=?",
                (resultado['valencia_sugerida'], resultado['justificacion_llm'], fila['id']),
            )
        procesadas += 1
        if verbose:
            signo = {-1: '−', 0: '○', 1: '+'}.get(resultado['valencia_sugerida'], '?')
            print(f"  [{signo}] {fila['candidato'][:12]} | {fila['titular'][:55]}")

    return procesadas


if __name__ == '__main__':
    n = procesar_pendientes()
    print(f"\nTotal procesadas: {n}")
