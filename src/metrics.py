import numpy as np
import pandas as pd

def annual_return_pct(prices: pd.Series) -> float:
    s = prices.dropna()
    if len(s) < 2:
        return np.nan
    first = s.iloc[0]
    last = s.iloc[-1]
    if first == 0 or np.isnan(first) or np.isnan(last):
        return np.nan
    return (last - first) / first * 100.0

def annualized_vol_pct(prices: pd.Series) -> float:
    s = prices.dropna()
    if len(s) < 2:
        return np.nan
    rets = np.log(s / s.shift(1)).dropna()
    if len(rets) < 2:
        return np.nan
    vol = rets.std(ddof=1) * np.sqrt(252)
    return float(vol * 100.0)

def max_drawdown_pct(prices: pd.Series) -> float:
    s = prices.dropna()
    if len(s) < 2:
        return np.nan
    cummax = s.cummax()
    dd = (s / cummax) - 1.0  # <= 0
    mdd = dd.min()           # más negativo
    return float(mdd * 100.0)  # negativo o 0

def compute_metrics(prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve DataFrame con index=empresa y columnas:
      - return_pct
      - vol_pct
      - max_drawdown_pct (<=0)
    """
    rows = []
    for col in prices_df.columns:
        p = prices_df[col]
        rows.append({
            "ticker": col,
            "return_pct": annual_return_pct(p),
            "vol_pct": annualized_vol_pct(p),
            "max_drawdown_pct": max_drawdown_pct(p),
        })
    out = pd.DataFrame(rows).set_index("ticker")
    return out
