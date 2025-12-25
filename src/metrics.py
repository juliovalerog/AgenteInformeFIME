import numpy as np
import pandas as pd

TRADING_DAYS = 252


def annual_return_pct(prices: pd.Series) -> float:
    """Calcula la rentabilidad total del periodo (en %)."""
    s = prices.dropna()
    if len(s) < 2:
        return np.nan
    first = s.iloc[0]
    last = s.iloc[-1]
    if first == 0 or np.isnan(first) or np.isnan(last):
        return np.nan
    return (last - first) / first * 100.0


def annualized_vol_pct(prices: pd.Series) -> float:
    """Calcula la volatilidad anualizada (en %)."""
    s = prices.dropna()
    if len(s) < 2:
        return np.nan
    rets = np.log(s / s.shift(1)).dropna()
    if len(rets) < 2:
        return np.nan
    vol = rets.std(ddof=1) * np.sqrt(TRADING_DAYS)
    return float(vol * 100.0)


def max_drawdown_pct(prices: pd.Series) -> float:
    """Calcula el max drawdown del periodo (en %, negativo o 0)."""
    s = prices.dropna()
    if len(s) < 2:
        return np.nan
    cummax = s.cummax()
    drawdown = (s / cummax) - 1.0  # <= 0
    mdd = drawdown.min()  # mas negativo
    return float(mdd * 100.0)


def compute_metrics(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Calcula metricas por ticker a partir del DataFrame de precios."""
    rows = []
    for col in prices_df.columns:
        p = prices_df[col]
        rows.append(
            {
                "ticker": col,
                "return_pct": annual_return_pct(p),
                "vol_pct": annualized_vol_pct(p),
                "max_drawdown_pct": max_drawdown_pct(p),
            }
        )
    return pd.DataFrame(rows).set_index("ticker")
