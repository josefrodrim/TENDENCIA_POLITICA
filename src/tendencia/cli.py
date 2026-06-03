"""
CLI principal del pipeline.

Uso:
  python -m tendencia.cli captura --fecha 2026-06-02
  python -m tendencia.cli captura --rango
  python -m tendencia.cli exportar
  python -m tendencia.cli kappa
"""
from __future__ import annotations

import argparse
from datetime import date


def cmd_captura(args: argparse.Namespace) -> None:
    from tendencia.pipeline import correr_fecha, correr_rango
    if args.fecha:
        print(f"Capturando {args.fecha}…")
        correr_fecha(args.fecha)
    else:
        from tendencia.config import FECHA_FIN, FECHA_INICIO
        print(f"Corriendo rango {FECHA_INICIO} → {FECHA_FIN}…")
        correr_rango()


def cmd_exportar(args: argparse.Namespace) -> None:
    from tendencia.config import DB_PATH, REPORTS_DIR
    from tendencia.db import exportar_csv, init_db
    init_db(DB_PATH)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    destino = REPORTS_DIR / f"titulares_{date.today().isoformat()}.csv"
    exportar_csv(destino, db_path=DB_PATH)
    print(f"CSV exportado → {destino}")


def cmd_recuperar(args: argparse.Namespace) -> None:
    """Recupera histórico via Wayback Machine para fechas no cubiertas por RSS."""
    from tendencia.wayback import recuperar_fecha, recuperar_rango
    if args.fecha:
        print(f"Recuperando {args.fecha} vía Wayback…")
        recuperar_fecha(args.fecha)
    else:
        desde = args.desde
        hasta = args.hasta
        print(f"Recuperando rango {desde} → {hasta} vía Wayback…")
        recuperar_rango(desde, hasta)


def cmd_importar(args: argparse.Namespace) -> None:
    """Lee el CSV codificado manualmente y actualiza valencia_humana en la BD."""
    import csv
    from tendencia.config import DB_PATH
    from tendencia.db import actualizar_humano
    ruta = args.csv
    with open(ruta, newline='', encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    n = actualizar_humano(filas, db_path=DB_PATH)
    print(f"{n} filas actualizadas en la BD desde {ruta}")


def cmd_valencia(args: argparse.Namespace) -> None:
    from tendencia.llm import procesar_pendientes
    limite = args.limite
    n = procesar_pendientes(limite=limite)
    print(f"\nTotal procesadas: {n}")


def cmd_reporte(args: argparse.Namespace) -> None:
    from tendencia.reports.html import generar
    ruta = generar()
    print(f"Reporte generado → {ruta}")


def cmd_kappa(args: argparse.Namespace) -> None:
    from tendencia.kappa import calcular_kappa
    r = calcular_kappa()
    if r['kappa'] is None:
        print(f"Sin datos suficientes: {r['mensaje']}")
    else:
        print(f"Cohen's kappa = {r['kappa']}  ({r['nivel']})")
        print(f"Filas evaluadas: {r['n']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog='tendencia', description='Pipeline cobertura electoral Perú')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_cap = sub.add_parser('captura', help='Capturar titulares de diarios')
    p_cap.add_argument('--fecha', metavar='YYYY-MM-DD', help='Fecha específica (default: rango completo)')
    p_cap.set_defaults(func=cmd_captura)

    p_exp = sub.add_parser('exportar', help='Exportar BD a CSV')
    p_exp.set_defaults(func=cmd_exportar)

    p_rec = sub.add_parser('recuperar', help='Recuperar histórico via Wayback Machine')
    p_rec.add_argument('--fecha',  metavar='YYYY-MM-DD', help='Fecha específica')
    p_rec.add_argument('--desde',  metavar='YYYY-MM-DD', help='Inicio del rango')
    p_rec.add_argument('--hasta',  metavar='YYYY-MM-DD', help='Fin del rango')
    p_rec.set_defaults(func=cmd_recuperar)

    p_imp = sub.add_parser('importar', help='Importar valencia_humana desde CSV codificado')
    p_imp.add_argument('csv', metavar='archivo.csv', help='CSV con columnas valencia_humana y foto_tono ya completadas')
    p_imp.set_defaults(func=cmd_importar)

    p_val = sub.add_parser('valencia', help='Proponer valencia con LLM (filas pendientes, opcional)')
    p_val.add_argument('--limite', type=int, default=None, metavar='N', help='Máximo de filas a procesar')
    p_val.set_defaults(func=cmd_valencia)

    p_rep = sub.add_parser('reporte', help='Generar reporte HTML')
    p_rep.set_defaults(func=cmd_reporte)

    p_kap = sub.add_parser('kappa', help='Calcular Cohen\'s kappa LLM vs humano')
    p_kap.set_defaults(func=cmd_kappa)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
