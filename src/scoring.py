import numpy as np
import pandas as pd
from .config import ScoringConfig

def _minmax_0_1(series: pd.Series, higher_is_better: bool) -> pd.Series:
    s = series.astype(float)
    valid = s.replace([np.inf, -np.inf], np.nan)
    mn = valid.min(skipna=True)
    mx = valid.max(skipna=True)

    # Si no hay rango, devolvemos 0.5 donde haya dato (neutral) y NaN donde no.
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return valid.apply(lambda x: 0.5 if not pd.isna(x) else np.nan)

    scaled = (valid - mn) / (mx - mn)
    if not higher_is_better:
        scaled = 1.0 - scaled
    return scaled

def add_score(metrics_df: pd.DataFrame, cfg: ScoringConfig) -> pd.DataFrame:
    """
    Scoring determinista 1..10:
      - Normaliza (0..1) por columna usando min-max del propio universo (reproducible dado el input).
      - return: higher better
      - vol: lower better
      - drawdown: menos negativo (más cerca de 0) mejor => higher better sobre max_drawdown_pct
    Hard stops:
      if return < 0 OR abs(drawdown) > 40 OR vol > 50 => score=1
    """
    df = metrics_df.copy()

    # Flags hardstop
    hs = (
        (df["return_pct"] < cfg.hardstop_return_lt) |
        (df["vol_pct"] > cfg.hardstop_vol_gt) |
        (df["max_drawdown_pct"].abs() > cfg.hardstop_dd_gt)
    )

    r_norm = _minmax_0_1(df["return_pct"], higher_is_better=True)
    v_norm = _minmax_0_1(df["vol_pct"], higher_is_better=False)
    d_norm = _minmax_0_1(df["max_drawdown_pct"], higher_is_better=True)

    raw = cfg.w_return * r_norm + cfg.w_vol * v_norm + cfg.w_dd * d_norm

    # Escalar a 1..10 y redondear
    score_cont = cfg.score_min + raw * (cfg.score_max - cfg.score_min)
    score = score_cont.round().astype("Int64")

    # Aplicar hard stops
    score = score.mask(hs, cfg.score_min)

    df["score"] = score.fillna(cfg.score_min).astype(int)
    return df
