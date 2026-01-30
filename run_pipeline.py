import argparse
from pathlib import Path

from src.pipeline import run_deterministic_pipeline
from src.io_excel import export_results
from src.sectors import load_sectors, DEFAULT_SOURCE_URL
from src.llm_summary import generate_summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Ruta al Excel de precios (IBEX 35 2025)")
    parser.add_argument("--output", default="outputs/ibex35_metrics_scoring_2025.xlsx", help="Ruta del Excel de salida")
    parser.add_argument("--sectors", default="data/ibex35_ticker_sector_bmex.xlsx", help="Ruta al Excel de sectores")
    parser.add_argument("--sector-source-url", default=DEFAULT_SOURCE_URL, help="Fuente oficial de sectores")
    parser.add_argument("--summary-out", default="outputs/ibex35_summary.txt", help="Ruta del resumen ejecutivo")
    parser.add_argument("--model", default="gemini-flash-latest", help="Modelo Gemini")
    args = parser.parse_args()

    df = run_deterministic_pipeline(args.input)
    sectors = load_sectors(args.sectors, args.sector_source_url)
    df = df.join(sectors, how="left")
    export_results(df, args.output)

    summary = generate_summary(df, model=args.model)
    Path(args.summary_out).write_text(summary, encoding="utf-8")

    print("OK. Filas:", len(df))
    print("Salida:", args.output)
    print("Resumen:", args.summary_out)
    print(df.head(10))

if __name__ == "__main__":
    main()
