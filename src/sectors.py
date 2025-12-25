from __future__ import annotations

import pandas as pd

DEFAULT_SOURCE_URL = "https://www.bolsasymercados.es/"

def load_sectors(path: str, source_url: str = DEFAULT_SOURCE_URL) -> pd.DataFrame:
    """Carga sectores desde un Excel y devuelve un DataFrame indexado por ticker."""
    df = pd.read_excel(path)

    # Try common column names, fall back to first column.
    lower_cols = {c.lower(): c for c in df.columns}
    ticker_col = lower_cols.get("ticker") or lower_cols.get("symbol")
    if ticker_col is None:
        ticker_col = df.columns[0]

    sector_col = (
        lower_cols.get("sector")
        or lower_cols.get("sector_bmex")
        or lower_cols.get("sector_bme")
    )
    if sector_col is None:
        raise ValueError("No se encontro columna de sector en el Excel de sectores.")

    out = df[[ticker_col, sector_col]].copy()
    out.columns = ["ticker", "sector"]
    out["ticker"] = out["ticker"].astype(str).str.strip()
    out["sector"] = out["sector"].astype(str).str.strip()
    out["sector_source_url"] = source_url
    return out.set_index("ticker")
