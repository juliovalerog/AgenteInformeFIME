from __future__ import annotations

import json

import pandas as pd
import requests

def _top_rows(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    cols = ["rank", "score", "return_pct", "vol_pct", "max_drawdown_pct", "sector"]
    present = [c for c in cols if c in df.columns]
    return df.sort_values("rank").head(n)[present]

def _table_text(df: pd.DataFrame, cols: list[str]) -> str:
    present = [c for c in cols if c in df.columns]
    return df[present].to_string()

def _prompt_from_df(df: pd.DataFrame) -> str:
    top = _top_rows(df, n=5)
    top_text = top.reset_index().to_string(index=False)
    total = len(df)
    na_prices = int(df.get("has_na_prices", pd.Series(dtype=bool)).sum())
    na_metrics = int(df.get("has_na_metrics", pd.Series(dtype=bool)).sum())
    drawdown_pos = int(df.get("drawdown_positive", pd.Series(dtype=bool)).sum())

    return (
        "Eres un analista que redacta un resumen ejecutivo para comite.\n"
        "Maximo 10 lineas. No des recomendaciones de inversion.\n"
        "Explica que el scoring es determinista y con hard stops.\n"
        "Menciona limitaciones y el control de calidad.\n\n"
        f"Total de empresas: {total}\n"
        f"Flags: has_na_prices={na_prices}, has_na_metrics={na_metrics}, "
        f"drawdown_positive={drawdown_pos}\n\n"
        "Top 5 (ordenado por rank):\n"
        f"{top_text}\n"
    )

def _ollama_generate(prompt: str, model: str, timeout_s: int = 180) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as exc:
        return f"Resumen no disponible. Error al invocar Ollama: {exc}"

def generate_summary(
    df: pd.DataFrame,
    model: str,
    max_lines: int = 10,
    timeout_s: int = 180,
) -> str:
    prompt = _prompt_from_df(df)
    text = _ollama_generate(prompt, model=model, timeout_s=timeout_s)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])

def generate_analysis_ibex(df: pd.DataFrame, model: str, timeout_s: int = 180) -> str:
    cols = [
        "return_pct",
        "vol_pct",
        "max_drawdown_pct",
        "sector",
        "score",
    ]
    top5 = df.sort_values("return_pct", ascending=False).head(5)
    bottom5 = df.sort_values("return_pct", ascending=True).head(5)
    table_text = _table_text(df, ["return_pct", "vol_pct", "max_drawdown_pct", "sector", "score"])

    prompt = (
        "Actua como analista financiero preparando un resumen para un comite de inversion.\n"
        "Input: tabla con metricas 2025 del IBEX 35 (rentabilidad, volatilidad, drawdown por empresa).\n"
        "No realices calculos nuevos ni ajustes metricas.\n"
        "1. Identifica las 5 empresas con mayor y 5 con menor rentabilidad.\n"
        "2. Describe su comportamiento citando explicitamente las metricas relevantes.\n"
        "3. Redacta un resumen ejecutivo (max. 8 lineas) en lenguaje claro y profesional.\n"
        "4. Separa hechos de interpretacion.\n"
        "5. Anade 1-2 limitaciones del analisis.\n"
        "Formato de salida: titulos breves + parrafo final.\n"
        "No infieras causalidad ni uses informacion externa.\n\n"
        "Top 5 por rentabilidad:\n"
        f"{_table_text(top5, cols)}\n\n"
        "Bottom 5 por rentabilidad:\n"
        f"{_table_text(bottom5, cols)}\n\n"
        "Tabla completa:\n"
        f"{table_text}\n"
    )
    return _ollama_generate(prompt, model=model, timeout_s=timeout_s)

def generate_sector_comparison(df: pd.DataFrame, model: str, timeout_s: int = 180) -> str:
    prompt = (
        "Actua como analista financiero preparando una comparativa interna.\n"
        "Input: tabla de metricas 2025 del IBEX 35 (rentabilidad, volatilidad, drawdown).\n"
        "Criterios de comparacion: rentabilidad, volatilidad, drawdown (solo estos).\n"
        "1. Agrupa empresas en banca, utilities e industriales.\n"
        "2. Compara los grupos exclusivamente con los criterios definidos.\n"
        "3. Clasifica cada grupo por perfil de riesgo relativo (alto / medio / bajo).\n"
        "Formato: tabla comparativa + 3 bullets de sintesis.\n"
        "No uses datos externos ni conclusiones causales.\n"
        "Incluye 1 limitacion del analisis.\n\n"
        "Tabla completa:\n"
        f"{_table_text(df, ['sector', 'return_pct', 'vol_pct', 'max_drawdown_pct'])}\n"
    )
    return _ollama_generate(prompt, model=model, timeout_s=timeout_s)

def generate_portfolio_suggestion(df: pd.DataFrame, model: str, timeout_s: int = 180) -> str:
    prompt = (
        "Actua como gestor de inversiones preparando una propuesta preliminar.\n"
        "Input: metricas 2025 del IBEX 35 (rentabilidad, volatilidad, drawdown).\n"
        "Tarea: selecciona exactamente 5 valores diversificados.\n"
        "Busca equilibrio entre rentabilidad y riesgo, con diversificacion sectorial.\n"
        "Reglas (obligatorias):\n"
        "- Usa solo tickers presentes en la tabla.\n"
        "- No uses datos externos ni lenguaje concluyente.\n"
        "- La tabla de pesos debe tener 5 filas (una por ticker) y una fila TOTAL.\n"
        "- Cada peso debe ser exactamente 20% y la suma 100%.\n"
        "- No repitas tickers.\n"
        "Formato estricto:\n"
        "A) Tabla Seleccion (5 filas): | Ticker | Sector | Return_Pct | Vol_Pct | Max_Drawdown_Pct | Score |\n"
        "B) Tabla Pesos (6 filas): | Ticker | Peso (%) | y ultima fila TOTAL = 100%.\n"
        "C) Justificacion breve (3-5 lineas) explicando por que esos 5 equilibran rentabilidad/riesgo y diversificacion.\n\n"
        "Tabla completa:\n"
        f"{_table_text(df, ['sector', 'return_pct', 'vol_pct', 'max_drawdown_pct', 'score'])}\n"
    )
    return _ollama_generate(prompt, model=model, timeout_s=timeout_s)

def join_sections(sections: list[tuple[str, str]]) -> str:
    parts = []
    for title, body in sections:
        parts.append(f"## {title}")
        parts.append(body.strip())
        parts.append("")
    return "\n".join(parts).strip()
