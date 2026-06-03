"""
Generador de reporte HTML con Jinja2 + matplotlib.
Produce un archivo HTML autocontenido con:
  - Resumen ejecutivo
  - Tabla por diario × candidato
  - Gráfico: distribución de valencia_humana
  - Gráfico: línea temporal de apariciones
  - Nota metodológica de neutralidad
"""
from __future__ import annotations

import base64
import io
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from jinja2 import Environment, BaseLoader

from tendencia.config import (
    CANDIDATO_A, CANDIDATO_B, DB_PATH,
    FECHA_FIN, FECHA_INICIO, REPORTS_DIR,
)
from tendencia.db import get_conn

# ── Queries ─────────────────────────────────────────────────────────────────

_SQL_DATOS = """
SELECT diario, fecha, candidato, es_opinion,
       posicion, tiene_foto, valencia_humana, valencia_sugerida
FROM   titulares
WHERE  candidato != 'ninguno'
ORDER  BY fecha, diario
"""

_SQL_TOTALES = """
SELECT candidato,
       COUNT(*)                                      AS apariciones,
       SUM(CASE WHEN posicion = 1 THEN 1 ELSE 0 END) AS titular_principal,
       SUM(tiene_foto)                                AS con_foto,
       SUM(CASE WHEN es_opinion = 0 THEN 1 ELSE 0 END) AS noticias,
       SUM(CASE WHEN es_opinion = 1 THEN 1 ELSE 0 END) AS opinion
FROM   titulares
WHERE  candidato != 'ninguno'
GROUP  BY candidato
"""

_SQL_POR_DIARIO = """
SELECT diario, candidato,
       COUNT(*)                                        AS apariciones,
       SUM(CASE WHEN posicion = 1 THEN 1 ELSE 0 END)   AS titular_principal,
       ROUND(100.0 * SUM(tiene_foto) / COUNT(*), 1)    AS pct_foto,
       SUM(CASE WHEN es_opinion = 0 THEN 1 ELSE 0 END) AS noticias,
       SUM(CASE WHEN es_opinion = 1 THEN 1 ELSE 0 END) AS opinion
FROM   titulares
WHERE  candidato != 'ninguno'
GROUP  BY diario, candidato
ORDER  BY diario, candidato
"""


# ── Helpers de gráficos ──────────────────────────────────────────────────────

def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _grafico_valencia(df: pd.DataFrame) -> str:
    """Barras apiladas de valencia_humana por candidato × diario."""
    sub = df[df['valencia_humana'].notna()].copy()
    if sub.empty:
        sub = df[df['valencia_sugerida'].notna()].copy()
        col = 'valencia_sugerida'
        nota = '(LLM — sin validación humana)'
    else:
        col = 'valencia_humana'
        nota = '(validada por investigador)'

    if sub.empty:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, 'Sin datos de valencia aún', ha='center', va='center')
        ax.axis('off')
        return _fig_to_b64(fig)

    pivot = (
        sub.groupby(['diario', col]).size()
        .unstack(fill_value=0)
        .reindex(columns=[-1, 0, 1], fill_value=0)
    )
    colors = {-1: '#e74c3c', 0: '#95a5a6', 1: '#2ecc71'}
    labels = {-1: 'Negativa (−1)', 0: 'Neutra (0)', 1: 'Positiva (+1)'}

    fig, ax = plt.subplots(figsize=(9, max(3, len(pivot) * 0.5 + 1)))
    bottom = pd.Series(0, index=pivot.index)
    for v in [-1, 0, 1]:
        if v in pivot.columns:
            ax.barh(pivot.index, pivot[v], left=bottom, color=colors[v], label=labels[v])
            bottom += pivot[v]
    ax.set_xlabel('Número de artículos')
    ax.set_title(f'Distribución de valencia por diario {nota}')
    ax.legend(loc='lower right', fontsize=8)
    fig.tight_layout()
    return _fig_to_b64(fig)


def _grafico_temporal(df: pd.DataFrame) -> str:
    """Línea temporal: apariciones por día por candidato."""
    conteo = df.groupby(['fecha', 'candidato']).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 4))
    for cand in conteo.columns:
        ax.plot(conteo.index, conteo[cand], marker='o', markersize=4, label=cand)
    ax.set_xlabel('Fecha')
    ax.set_ylabel('Artículos')
    ax.set_title('Apariciones diarias por candidato (todos los diarios)')
    ax.legend()
    plt.xticks(rotation=45, ha='right', fontsize=7)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ── Template HTML ────────────────────────────────────────────────────────────

_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Análisis cobertura electoral Perú — {{ fecha_ini }} al {{ fecha_fin }}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #222; }
    h1 { border-bottom: 3px solid #c0392b; padding-bottom: .5rem; }
    h2 { color: #c0392b; margin-top: 2rem; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .9rem; }
    th, td { border: 1px solid #ddd; padding: .45rem .7rem; text-align: center; }
    th { background: #f4f4f4; }
    td.label { text-align: left; font-weight: 500; }
    .nota { background: #fef9e7; border-left: 4px solid #f39c12; padding: .8rem 1rem; margin: 1.5rem 0; font-size: .9rem; }
    .alerta { background: #fdedec; border-left: 4px solid #c0392b; padding: .8rem 1rem; margin: 1.5rem 0; font-size: .9rem; }
    img.chart { max-width: 100%; margin: 1rem 0; border: 1px solid #eee; border-radius: 4px; }
    footer { color: #888; font-size: .8rem; margin-top: 3rem; border-top: 1px solid #eee; padding-top: 1rem; }
  </style>
</head>
<body>

<h1>Análisis de cobertura electoral — Segunda vuelta Perú 2026</h1>
<p><strong>Período:</strong> {{ fecha_ini }} al {{ fecha_fin }} &nbsp;|&nbsp;
   <strong>Diarios:</strong> {{ n_diarios }} &nbsp;|&nbsp;
   <strong>Generado:</strong> {{ hoy }}</p>

<div class="nota">
  <strong>Nota metodológica:</strong> Este análisis es <em>descriptivo y neutral</em>.
  Mide el espacio y la valencia que cada diario dedica a cada candidato con los mismos criterios.
  Una asimetría observada en la cobertura <strong>no equivale por sí sola a intención editorial</strong>:
  es un dato empírico que el lector debe interpretar en su contexto.
  La valencia reportada corresponde a <code>valencia_humana</code> (codificada manualmente por el investigador).
  Las filas sin validación humana se excluyen del análisis de valencia.
</div>

<h2>Resumen ejecutivo</h2>
<table>
  <tr><th>Candidato</th><th>Apariciones totales</th><th>Titular principal (pos=1)</th>
      <th>Con foto (%)</th><th>Noticias</th><th>Opinión</th></tr>
  {% for r in totales %}
  <tr>
    <td class="label">{{ r.candidato }}</td>
    <td>{{ r.apariciones }}</td>
    <td>{{ r.titular_principal }}</td>
    <td>{{ "%.1f"|format(100.0 * r.con_foto / r.apariciones if r.apariciones else 0) }}%</td>
    <td>{{ r.noticias }}</td>
    <td>{{ r.opinion }}</td>
  </tr>
  {% endfor %}
</table>

<h2>Apariciones diarias</h2>
<img class="chart" src="data:image/png;base64,{{ img_temporal }}" alt="Línea temporal">

<h2>Valencia por diario</h2>
{% if sin_humana %}
<div class="alerta">⚠ Aún no hay filas con <code>valencia_humana</code> registrada.
El gráfico muestra <code>valencia_sugerida</code> (LLM) como referencia provisional.
<strong>No usar para conclusiones sin validación humana.</strong></div>
{% endif %}
<img class="chart" src="data:image/png;base64,{{ img_valencia }}" alt="Distribución de valencia">

<h2>Detalle por diario y candidato</h2>
<table>
  <tr><th>Diario</th><th>Candidato</th><th>Apariciones</th>
      <th>Titular ppal</th><th>Con foto %</th><th>Noticias</th><th>Opinión</th></tr>
  {% for r in por_diario %}
  <tr>
    <td class="label">{{ r.diario }}</td>
    <td>{{ r.candidato }}</td>
    <td>{{ r.apariciones }}</td>
    <td>{{ r.titular_principal }}</td>
    <td>{{ r.pct_foto }}%</td>
    <td>{{ r.noticias }}</td>
    <td>{{ r.opinion }}</td>
  </tr>
  {% endfor %}
</table>

<footer>
  Proyecto: Análisis de cobertura de prensa — Elecciones Perú segunda vuelta 2026.<br>
  Los datos provienen de scraping de portadas web a las 07:00 hora Perú.<br>
  Generado el {{ hoy }}.
</footer>
</body>
</html>"""


# ── Función principal ────────────────────────────────────────────────────────

def generar(destino: Path | None = None) -> Path:
    conn  = get_conn(DB_PATH)
    df    = pd.read_sql_query(_SQL_DATOS, conn)
    tots  = [dict(r) for r in conn.execute(_SQL_TOTALES).fetchall()]
    xdiar = [dict(r) for r in conn.execute(_SQL_POR_DIARIO).fetchall()]
    conn.close()

    sin_humana = df['valencia_humana'].isna().all()
    n_diarios  = df['diario'].nunique()

    img_temporal = _grafico_temporal(df)
    img_valencia = _grafico_valencia(df)

    env  = Environment(loader=BaseLoader())
    tmpl = env.from_string(_TEMPLATE)
    html = tmpl.render(
        fecha_ini=FECHA_INICIO or 'N/D',
        fecha_fin=FECHA_FIN    or 'N/D',
        hoy=date.today().isoformat(),
        n_diarios=n_diarios,
        totales=tots,
        por_diario=xdiar,
        img_temporal=img_temporal,
        img_valencia=img_valencia,
        sin_humana=sin_humana,
    )

    if destino is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        destino = REPORTS_DIR / f"reporte_{date.today().isoformat()}.html"

    destino.write_text(html, encoding='utf-8')
    return destino


if __name__ == '__main__':
    ruta = generar()
    print(f"Reporte generado → {ruta}")
