import numpy as np
import pandas as pd

from .config import ScoringConfig


def _minmax_0_1(series: pd.Series, higher_is_better: bool) -> pd.Series:
    """Normaliza una serie a 0..1 usando min-max del universo actual."""
    s = series.astype(float)
    valid = s.replace([np.inf, -np.inf], np.nan)
    mn = valid.min(skipna=True)
    mx = valid.max(skipna=True)

    # Si no hay rango, devolvemos 0.5 donde haya dato (neutral).
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return valid.apply(lambda x: 0.5 if not pd.isna(x) else np.nan)

    scaled = (valid - mn) / (mx - mn)
    if not higher_is_better:
        scaled = 1.0 - scaled
    return scaled


def _hardstop_mask(metrics: pd.DataFrame, cfg: ScoringConfig) -> pd.Series:
    """Marca filas que deben quedar con score minimo por reglas de control."""
    return (
        (metrics["return_pct"] < cfg.hardstop_return_lt)
        | (metrics["vol_pct"] > cfg.hardstop_vol_gt)
        | (metrics["max_drawdown_pct"].abs() > cfg.hardstop_dd_gt)
    )


def add_score(metrics_df: pd.DataFrame, cfg: ScoringConfig) -> pd.DataFrame:
    """Calcula el score determinista (1..10) a partir de metricas."""
    df = metrics_df.copy()

    r_norm = _minmax_0_1(df["return_pct"], higher_is_better=True)
    v_norm = _minmax_0_1(df["vol_pct"], higher_is_better=False)
    d_norm = _minmax_0_1(df["max_drawdown_pct"], higher_is_better=True)

    raw = cfg.w_return * r_norm + cfg.w_vol * v_norm + cfg.w_dd * d_norm

    # Escalar a 1..10 y redondear a entero.
    score_cont = cfg.score_min + raw * (cfg.score_max - cfg.score_min)
    score = score_cont.round().astype("Int64")

    # Aplicar hard stops (reglas de seguridad).
    score = score.mask(_hardstop_mask(df, cfg), cfg.score_min)

    df["score"] = score.fillna(cfg.score_min).astype(int)
    return df
