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

    p_kap = sub.add_parser('kappa', help='Calcular Cohen\'s kappa LLM vs humano')
    p_kap.set_defaults(func=cmd_kappa)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
