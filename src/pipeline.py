import pandas as pd

from .config import ScoringConfig
from .io_excel import read_prices_excel
from .metrics import compute_metrics
from .scoring import add_score

def quality_flags(prices: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    """Genera banderas simples de calidad para trazabilidad."""
    flags = pd.DataFrame(index=metrics.index)
    flags["has_na_prices"] = prices.isna().any(axis=0)
    flags["has_na_metrics"] = metrics.isna().any(axis=1)
    flags["drawdown_positive"] = metrics["max_drawdown_pct"] > 0
    return flags

def run_deterministic_pipeline(input_excel_path: str) -> pd.DataFrame:
    """Ejecuta el pipeline determinista de principio a fin."""
    prices = read_prices_excel(input_excel_path)

    # Validacion minima: fechas ordenadas ascendentemente.
    if not prices.index.is_monotonic_increasing:
        raise ValueError("Las fechas no estan ordenadas ascendentemente tras la carga.")

    # Validacion minima: control NA global (no paramos, solo queda reflejado en flags).
    metrics = compute_metrics(prices)

    cfg = ScoringConfig()
    scored = add_score(metrics, cfg)
    flags = quality_flags(prices, metrics)

    out = scored.join(flags)

    # Ranking determinista con orden estable.
    out = out.sort_values(
        by=["score", "return_pct", "vol_pct", "max_drawdown_pct"],
        ascending=[False, False, True, False],
        kind="mergesort"
    )
    out["rank"] = range(1, len(out) + 1)

    return out
