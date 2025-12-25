from __future__ import annotations

import json

import pandas as pd
import requests


def _table_text(df: pd.DataFrame, cols: list[str]) -> str:
    """Convierte un subconjunto de columnas a texto plano para el prompt."""
    present = [c for c in cols if c in df.columns]
    return df[present].to_string()


def _ollama_generate(prompt: str, model: str, timeout_s: int = 180) -> str:
    """Llama a Ollama local y devuelve texto o un mensaje de error controlado."""
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


def generate_analysis_ibex(df: pd.DataFrame, model: str, timeout_s: int = 180) -> str:
    """Genera un resumen ejecutivo (top/bottom) usando solo datos internos."""
    cols = [
        "return_pct",
        "vol_pct",
        "max_drawdown_pct",
        "sector",
        "score",
    ]
    top5 = df.sort_values("return_pct", ascending=False).head(5)
    bottom5 = df.sort_values("return_pct", ascending=True).head(5)
    table_text = _table_text(df, cols)

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
    """Genera comparativas por sectores usando solo la tabla interna."""
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


def generate_portfolio_suggestion(
    df: pd.DataFrame,
    model: str,
    timeout_s: int = 180,
) -> str:
    """Pide al LLM una propuesta de 5 valores con pesos fijos del 20%."""
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
    """Une secciones en un unico Markdown con titulos H2."""
    parts = []
    for title, body in sections:
        parts.append(f"## {title}")
        parts.append(body.strip())
        parts.append("")
    return "\n".join(parts).strip()
