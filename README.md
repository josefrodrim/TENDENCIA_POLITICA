# Tendencia Política — Análisis de cobertura de prensa

Pipeline en Python para recolectar y analizar titulares de portada de los principales
diarios peruanos durante la segunda vuelta electoral.

## Pregunta de investigación

> ¿Qué espacio y qué valencia dedica cada diario a cada candidato, día a día?

Este análisis es **descriptivo y neutral**: mide a ambos candidatos con la misma vara.
Una asimetría observada en la cobertura no equivale por sí sola a intención editorial;
es un dato empírico que el lector debe interpretar en su contexto.

## Configuración inicial

```bash
# 1. Instalar dependencias
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configurar parámetros
cp .env.example .env
# Editar .env: FECHA_INICIO, FECHA_FIN, CANDIDATO_A, CANDIDATO_B, TERMINOS_*, ANTHROPIC_API_KEY

# 3. Inicializar base de datos
python -c "from tendencia.db import init_db; init_db()"
```

## Uso

```bash
# Correr tests
pytest

# Capturar titulares de un día (una vez implementados los scrapers)
python -m tendencia.cli captura --fecha 2025-06-10

# Exportar a CSV
python -m tendencia.cli exportar

# Calcular Cohen's kappa (requiere valencia_humana en la BD)
python -m tendencia.kappa

# Generar reporte HTML
python -m tendencia.cli reporte
```

## Diarios objetivo

| Diario        | Estado   |
|---------------|----------|
| La República  | Fase 2   |
| El Comercio   | Fase 2   |
| Perú21        | Pendiente |
| Trome         | Pendiente |
| Correo        | Pendiente |
| Expreso       | Pendiente |
| El Popular    | Pendiente |
| Ojo           | Pendiente |
| La Razón      | Pendiente |
| Gestión       | Pendiente |

Los diarios cuyo `robots.txt` prohíba el scraping quedarán registrados como
`excluido_por_robots` en la tabla de metadatos.

## Metodología de codificación

- **candidato**: detectado por reglas léxicas (nombre/apellido/partido).
  Si aparecen ambos candidatos en el mismo titular, se genera una fila por candidato.
- **valencia_sugerida**: propuesta por LLM (−1 negativa / 0 neutra / +1 positiva).
  Es apoyo, no el dato de análisis.
- **valencia_humana**: la codifica el investigador manualmente. Es el dato principal.
- **Acuerdo inter-codificador**: Cohen's kappa entre `valencia_sugerida` y
  `valencia_humana` sobre las filas ya codificadas a mano.

## Estructura del proyecto

```
src/tendencia/
  config.py       # Parámetros (lee de .env)
  schema.py       # TypedDict Titular — esquema común de todas las filas
  db.py           # SQLite: init, insertar, exportar CSV
  detection.py    # Detección de candidato por reglas léxicas
  llm.py          # Valencia sugerida via API Anthropic
  kappa.py        # Cohen's kappa
  scrapers/
    base.py       # Utilidades comunes: robots.txt, delay, User-Agent
    larepublica.py
    ...
  reports/
    html.py       # Reporte HTML con Jinja2
tests/
  fixtures/       # HTML guardado para tests sin red
  test_schema.py
  test_detection.py
  scrapers/
data/             # titulares.db (en .gitignore)
reports/output/   # HTML generados (en .gitignore)
```
