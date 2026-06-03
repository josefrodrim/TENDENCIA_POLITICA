"""
Calcula Cohen's kappa entre valencia_sugerida (LLM) y valencia_humana (investigador).
Solo opera sobre filas donde ambos valores están presentes.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

from tendencia.config import DB_PATH


def calcular_kappa(db_path: Path = DB_PATH) -> dict:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT valencia_sugerida, valencia_humana
        FROM   titulares
        WHERE  valencia_sugerida IS NOT NULL
          AND  valencia_humana   IS NOT NULL
        """
    ).fetchall()
    conn.close()

    if len(rows) < 2:
        return {"kappa": None, "n": len(rows), "mensaje": "Insuficientes filas codificadas."}

    llm    = [r[0] for r in rows]
    humana = [r[1] for r in rows]
    kappa  = cohen_kappa_score(humana, llm, labels=[-1, 0, 1])

    nivel = (
        "excelente (≥0.80)" if kappa >= 0.80
        else "bueno (0.60–0.79)" if kappa >= 0.60
        else "moderado (0.40–0.59)" if kappa >= 0.40
        else "débil (<0.40)"
    )

    return {"kappa": round(kappa, 4), "n": len(rows), "nivel": nivel}


if __name__ == "__main__":
    resultado = calcular_kappa()
    print(f"Cohen's kappa = {resultado['kappa']}  ({resultado.get('nivel', '')})")
    print(f"Filas evaluadas: {resultado['n']}")
