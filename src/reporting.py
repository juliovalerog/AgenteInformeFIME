from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Serializa un DataFrame a bytes de Excel (para descargas en Streamlit)."""
    buf = BytesIO()
    df.to_excel(buf, index=True)
    buf.seek(0)
    return buf.getvalue()


def normalize_price_series(series: pd.Series) -> pd.Series:
    """Normaliza una serie de precios a base 100."""
    s = series.dropna()
    if s.empty:
        return s
    base = s.iloc[0]
    if base == 0:
        return s * 0.0
    return s / base * 100.0


def plot_price_series(
    prices: pd.DataFrame,
    tickers: list[str],
    title: str,
    out_path: Path,
):
    """Grafica series de precios normalizadas y guarda el PNG."""
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(figsize=(10, 5))
    for ticker in tickers:
        if ticker not in prices.columns:
            continue
        s = normalize_price_series(prices[ticker])
        if s.empty:
            continue
        ax.plot(s.index, s.values, label=ticker, linewidth=1.6)

    ax.set_title(title)
    ax.set_ylabel("Indice (base 100)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", ncol=2, fontsize=8, frameon=False)
    locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    return fig


def plot_portfolio_series(
    prices: pd.DataFrame,
    tickers: list[str],
    weights: list[float],
    title: str,
    out_path: Path,
):
    """Grafica una cartera ponderada (base 100) y guarda el PNG."""
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    if not tickers or not weights:
        return None
    pairs = [(t, w) for t, w in zip(tickers, weights) if t in prices.columns]
    if not pairs:
        return None
    tickers_filtered, weights_filtered = zip(*pairs)
    weights_series = pd.Series(weights_filtered, index=tickers_filtered, dtype=float) / 100.0
    subset = prices[list(tickers_filtered)].dropna()
    if subset.empty:
        return None
    portfolio = (subset * weights_series).sum(axis=1)
    portfolio = normalize_price_series(portfolio)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(portfolio.index, portfolio.values, color="#2c3e50", linewidth=2.0, label="Cartera")
    ax.set_title(title)
    ax.set_ylabel("Indice (base 100)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    return fig


def markdown_to_paragraph_text(text: str) -> str:
    """Convierte markdown simple a etiquetas compatibles con ReportLab."""
    text = text.replace("`", "")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text


def clean_summary_lines(summary: str) -> list[str]:
    """Divide el resumen en lineas limpias para parsing."""
    return [line.rstrip() for line in summary.splitlines()]


def parse_markdown_table(lines: list[str]) -> tuple[list[list[str]], int]:
    """Parsea una tabla markdown y devuelve filas + lineas consumidas."""
    table_lines = []
    i = 0
    while i < len(lines) and is_table_line(lines[i]):
        table_lines.append(lines[i])
        i += 1
    if len(table_lines) < 2 or not is_separator_line(table_lines[1]):
        return [], 0
    header = [c.strip() for c in table_lines[0].strip("|").split("|")]
    rows = []
    for row_line in table_lines[2:]:
        if not is_table_line(row_line):
            break
        row = [c.strip() for c in row_line.strip("|").split("|")]
        rows.append(row)
    return [header] + rows, i


def is_table_line(line: str) -> bool:
    """Detecta lineas con separadores '|'."""
    return "|" in line


def is_separator_line(line: str) -> bool:
    """Detecta la linea separadora de cabeceras en markdown."""
    stripped = line.strip()
    if "|" not in stripped:
        return False
    allowed = set("|-: ")
    return set(stripped).issubset(allowed)


def extract_table_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """Extrae un bloque contiguo de lineas tipo tabla."""
    block = []
    i = start
    while i < len(lines) and is_table_line(lines[i]):
        block.append(lines[i])
        i += 1
    return block, i


def parse_table_block(block: list[str]) -> tuple[list[str], list[list[str]]]:
    """Parsea un bloque de tabla markdown a cabecera y filas."""
    if len(block) < 2 or not is_separator_line(block[1]):
        return [], []
    header = [c.strip() for c in block[0].strip("|").split("|")]
    rows = []
    for row_line in block[2:]:
        row = [c.strip() for c in row_line.strip("|").split("|")]
        rows.append(row)
    return header, rows


def _is_valid_ticker(value: str) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return text.upper() != "TOTAL"

def extract_selection_tickers(lines: list[str]) -> list[str]:
    """Busca la tabla de seleccion y devuelve tickers encontrados."""
    tickers = []
    i = 0
    while i < len(lines):
        if is_table_line(lines[i]) and i + 1 < len(lines) and is_separator_line(lines[i + 1]):
            block, end = extract_table_block(lines, i)
            header, rows = parse_table_block(block)
            if "Ticker" in header and "Sector" in header:
                idx = header.index("Ticker")
                for row in rows:
                    if len(row) > idx:
                        ticker = row[idx]
                        if _is_valid_ticker(ticker):
                            tickers.append(ticker)
                return tickers
            i = end
            continue
        i += 1
    return tickers


def normalize_weights(tickers: list[str]) -> list[float]:
    """Distribuye pesos y asegura suma 100% con limites simples."""
    n = len(tickers)
    if n == 0:
        return []
    weights = [100.0 / n] * n
    max_w = 20.0
    if max(weights) <= max_w:
        weights[-1] += 100.0 - sum(weights)
        return weights
    weights = [min(w, max_w) for w in weights]
    total = sum(weights)
    if total == 0:
        return weights
    factor = 100.0 / total
    weights = [w * factor for w in weights]
    weights[-1] += 100.0 - sum(weights)
    return weights


def format_weight_table(tickers: list[str], weights: list[float]) -> list[str]:
    """Construye una tabla markdown de pesos."""
    lines = ["| Ticker | Peso (%) |", "| --- | --- |"]
    for t, w in zip(tickers, weights):
        lines.append(f"| {t} | {w:.1f}% |")
    lines.append("| TOTAL | 100.0% |")
    return lines


def adjust_weights_in_report(
    report: str,
    fallback_tickers: list[str],
) -> tuple[str, list[str], list[float]]:
    """Fuerza pesos validos en el reporte y devuelve tickers usados."""
    lines = clean_summary_lines(report)
    tickers_fallback = extract_selection_tickers(lines) or fallback_tickers
    out_lines = []
    i = 0
    adjusted = False
    weights_used = []
    tickers_used = []
    while i < len(lines):
        if is_table_line(lines[i]) and i + 1 < len(lines) and is_separator_line(lines[i + 1]):
            block, end = extract_table_block(lines, i)
            header, rows = parse_table_block(block)
            if "Peso" in " ".join(header):
                idx = header.index("Ticker") if "Ticker" in header else None
                tickers = []
                if idx is not None:
                    for row in rows:
                        if len(row) > idx:
                            ticker = row[idx]
                            if _is_valid_ticker(ticker):
                                tickers.append(ticker)
                if not tickers:
                    tickers = tickers_fallback
                weights = normalize_weights(tickers)
                out_lines.extend(format_weight_table(tickers, weights))
                adjusted = True
                weights_used = weights
                tickers_used = tickers
                i = end
                continue
        out_lines.append(lines[i])
        i += 1
    if not adjusted and tickers_fallback:
        weights_used = normalize_weights(tickers_fallback)
        tickers_used = tickers_fallback
        out_lines.append("")
        out_lines.append("**pesos asignados:**")
        out_lines.extend(format_weight_table(tickers_fallback, weights_used))
    return "\n".join(out_lines), tickers_used, weights_used


def story_from_report(report: str) -> list:
    """Convierte el reporte markdown a elementos de ReportLab."""
    styles = getSampleStyleSheet()
    story = []
    lines = clean_summary_lines(report)
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            story.append(Spacer(1, 6))
            i += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(markdown_to_paragraph_text(line[3:]), styles["Heading2"]))
            story.append(Spacer(1, 6))
            i += 1
            continue
        if line.startswith("### "):
            story.append(Paragraph(markdown_to_paragraph_text(line[4:]), styles["Heading3"]))
            story.append(Spacer(1, 4))
            i += 1
            continue
        if line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            story.append(Paragraph(markdown_to_paragraph_text(line), styles["Heading3"]))
            story.append(Spacer(1, 4))
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and is_separator_line(lines[i + 1]):
            table_data, consumed = parse_markdown_table(lines[i:])
            if table_data:
                table = Table(table_data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONT", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 6))
                i += consumed
                continue

        bullet_prefixes = ("- ", "* ")
        if line.startswith(bullet_prefixes):
            line = line[2:]
            story.append(Paragraph(f"- {markdown_to_paragraph_text(line)}", styles["BodyText"]))
        else:
            story.append(Paragraph(markdown_to_paragraph_text(line), styles["BodyText"]))
            story.append(Spacer(1, 4))
        i += 1
    return story


def build_pdf(summary: str, df: pd.DataFrame, images: list[tuple[str, Path]]) -> bytes:
    """Genera un PDF con el resumen, tablas y graficas."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Informe ejecutivo", styles["Heading1"]))
    story.append(Spacer(1, 8))
    story.extend(story_from_report(summary))

    if images:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Graficas deterministas", styles["Heading2"]))
        story.append(Spacer(1, 6))
        max_width = A4[0] - doc.leftMargin - doc.rightMargin
        for title, path in images:
            story.append(Paragraph(title, styles["Heading3"]))
            story.append(Spacer(1, 4))
            try:
                img_reader = ImageReader(str(path))
                iw, ih = img_reader.getSize()
                scale = min(max_width / iw, 1.0)
                img = Image(str(path), width=iw * scale, height=ih * scale)
                story.append(img)
                story.append(Spacer(1, 8))
            except Exception:
                story.append(Paragraph(f"No se pudo cargar la imagen: {path}", styles["BodyText"]))
                story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Top 10", styles["Heading2"]))
    story.append(Spacer(1, 6))

    top = df.sort_values("rank").head(10).reset_index()
    cols = [
        "ticker",
        "rank",
        "score",
        "return_pct",
        "vol_pct",
        "max_drawdown_pct",
        "sector",
    ]
    present = [c for c in cols if c in top.columns]
    table_data = [present]
    for _, row in top[present].iterrows():
        table_data.append([_format_cell(row[c]) for c in present])

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONT", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _format_cell(value: object) -> str:
    """Formatea valores para tabla PDF."""
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
