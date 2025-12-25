from __future__ import annotations

from pathlib import Path
import shutil
from datetime import datetime

import pandas as pd
import streamlit as st

from src.config import ScoringConfig
from src.io_excel import read_prices_excel
from src.llm_summary import (
    generate_analysis_ibex,
    generate_portfolio_suggestion,
    generate_sector_comparison,
    join_sections,
)
from src.metrics import compute_metrics
from src.pipeline import quality_flags
from src.reporting import (
    adjust_weights_in_report,
    build_pdf,
    df_to_excel_bytes,
    plot_portfolio_series,
    plot_price_series,
)
from src.scoring import add_score
from src.sectors import DEFAULT_SOURCE_URL, load_sectors


def _show_plot(fig) -> None:
    if fig is None:
        return
    st.pyplot(fig)
    try:
        import matplotlib.pyplot as plt

        plt.close(fig)
    except Exception:
        pass


st.set_page_config(page_title="IBEX 35 Demo", layout="wide")

st.title("Demo: agente con razonamiento hibrido (LLM + reglas)")
st.markdown(
    "Flujo didactico paso a paso: calculo determinista, reglas y resumen LLM."
)

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Entrada")
    uploaded = st.file_uploader(
        "Sube el Excel de precios (Date + tickers)",
        type=["xlsx"],
    )
    st.caption(
        "Sectores se cargan por defecto desde: data/ibex35_ticker_sector_bmex.xlsx"
    )
    model = st.text_input("Modelo Ollama", value="llama3.2:3b")
    timeout_s = st.number_input("Timeout Ollama (segundos)", min_value=30, max_value=600, value=180, step=30)
    run_btn = st.button("Ejecutar pipeline", type="primary", use_container_width=True)

with right:
    if run_btn:
        st.session_state.pop("result_df", None)
        st.session_state.pop("summary_text", None)

        if uploaded is None:
            st.error("Falta el archivo de precios.")
        else:
            run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = Path("outputs") / run_ts
            run_dir.mkdir(parents=True, exist_ok=True)

            prices_path = run_dir / uploaded.name
            prices_path.write_bytes(uploaded.getbuffer())
            sectors_src = Path("data/ibex35_ticker_sector_bmex.xlsx")
            sectors_path = run_dir / sectors_src.name
            if sectors_src.exists():
                shutil.copy2(sectors_src, sectors_path)

            st.subheader("Paso 1. Carga y validacion (determinista)")
            prices = read_prices_excel(prices_path)
            st.write(f"Filas: {len(prices)} | Columnas (tickers): {len(prices.columns)}")
            st.write("Razonamiento: simbolico/determinista (reglas de carga).")
            st.dataframe(prices.head(5))

            st.subheader("Paso 2. Metricas (determinista)")
            metrics = compute_metrics(prices)
            st.write("Razonamiento: simbolico/determinista (formulas).")
            st.dataframe(metrics.head(10))

            st.subheader("Paso 3. Scoring y hard stops (determinista)")
            cfg = ScoringConfig()
            scored = add_score(metrics, cfg)
            st.write("Razonamiento: simbolico/determinista (reglas y pesos).")
            st.dataframe(scored.head(10))

            st.subheader("Paso 4. Flags de calidad (determinista)")
            flags = quality_flags(prices, metrics)
            st.write("Razonamiento: simbolico/determinista (control de NA y drawdown).")
            st.dataframe(flags.head(10))

            st.subheader("Paso 5. Ranking (determinista)")
            out = scored.join(flags)
            out = out.sort_values(
                by=["score", "return_pct", "vol_pct", "max_drawdown_pct"],
                ascending=[False, False, True, False],
                kind="mergesort",
            )
            out["rank"] = range(1, len(out) + 1)
            st.write("Razonamiento: simbolico/determinista (orden estable).")
            st.dataframe(out.head(10))

            st.subheader("Paso 6. Sectorizacion (externo controlado)")
            sectors = load_sectors(sectors_path, DEFAULT_SOURCE_URL)
            out = out.join(sectors, how="left")
            st.write("Razonamiento: enriquecimiento externo (solo reporting).")
            if "sector" in out.columns and out["sector"].nunique(dropna=False) == 1:
                st.warning(
                    "Todos los sectores son iguales. Revisa el archivo de sectores "
                    "porque no hay clasificacion real."
                )
            st.dataframe(out.head(10))

            st.subheader("Paso 7. Grafica top 5 (determinista)")
            top5 = out.sort_values("rank").head(5).index.tolist()
            top5_path = run_dir / "grafica_top5.png"
            fig = plot_price_series(prices, top5, "Top 5 por scoring (base 100)", top5_path)
            _show_plot(fig)

            st.subheader("Paso 8. Grafica bottom 5 (determinista)")
            bottom5 = out.sort_values("rank").tail(5).index.tolist()
            bottom5_path = run_dir / "grafica_bottom5.png"
            fig = plot_price_series(prices, bottom5, "Bottom 5 por scoring (base 100)", bottom5_path)
            _show_plot(fig)

            st.subheader("Paso 9. Analisis top/bottom y panorama general (LLM)")
            analysis_text = generate_analysis_ibex(out, model=model, timeout_s=timeout_s)
            st.write("Razonamiento: LLM con temperatura 0, sin datos externos.")
            st.code(analysis_text)

            st.subheader("Paso 10. Comparativa por sectores (LLM)")
            sector_text = generate_sector_comparison(out, model=model, timeout_s=timeout_s)
            st.write("Razonamiento: LLM con temperatura 0, comparativa interna.")
            st.code(sector_text)

            st.subheader("Paso 11. Sugerencia de cartera diversificada (LLM)")
            portfolio_text = generate_portfolio_suggestion(out, model=model, timeout_s=timeout_s)
            st.write("Razonamiento: LLM con temperatura 0, sin conclusiones causales.")
            st.code(portfolio_text)

            st.subheader("Paso 12. Informe final unificado")
            report = join_sections(
                [
                    ("Analisis IBEX 2025", analysis_text),
                    ("Comparativa por sectores", sector_text),
                    ("Sugerencia de cartera", portfolio_text),
                ]
            )
            report, tickers_used, weights_used = adjust_weights_in_report(
                report,
                fallback_tickers=out.sort_values("rank").head(8).index.tolist(),
            )
            st.code(report)

            st.subheader("Paso 13. Grafica cartera propuesta (determinista)")
            portfolio_path = run_dir / "grafica_cartera.png"
            fig = plot_portfolio_series(
                prices,
                tickers_used,
                weights_used,
                "Cartera propuesta (base 100)",
                portfolio_path,
            )
            _show_plot(fig)

            report_path = run_dir / "informe.md"
            report_path.write_text(report, encoding="utf-8")

            excel_path = run_dir / "ibex35_metrics_scoring_2025.xlsx"
            out.to_excel(excel_path, index=True)

            images = [
                ("Top 5 por scoring (base 100)", top5_path),
                ("Bottom 5 por scoring (base 100)", bottom5_path),
                ("Cartera propuesta (base 100)", portfolio_path),
            ]
            pdf_bytes = build_pdf(report, out, images)
            pdf_path = run_dir / "ibex35_summary.pdf"
            pdf_path.write_bytes(pdf_bytes)

            st.session_state["result_df"] = out
            st.session_state["summary_text"] = report
            st.session_state["pdf_bytes"] = pdf_bytes
            st.session_state["run_dir"] = run_dir

    if "result_df" in st.session_state:
        st.subheader("Descargas")
        result_df = st.session_state["result_df"]
        pdf_bytes = st.session_state.get("pdf_bytes", b"")
        run_dir = st.session_state.get("run_dir")

        st.download_button(
            "Descargar Excel",
            data=df_to_excel_bytes(result_df),
            file_name="ibex35_metrics_scoring_2025.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.download_button(
            "Descargar resumen PDF",
            data=pdf_bytes,
            file_name="ibex35_summary.pdf",
            mime="application/pdf",
        )
        if run_dir:
            st.caption(f"Salida almacenada en: {run_dir}")
