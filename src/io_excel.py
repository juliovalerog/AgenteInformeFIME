from pathlib import Path

import pandas as pd


def read_prices_excel(path: str | Path) -> pd.DataFrame:
    """Lee un Excel de precios con una columna Date y una columna por ticker.

    Devuelve un DataFrame indexado por fecha (datetime) y con tickers en columnas.
    """
    df = pd.read_excel(Path(path))

    if "Date" not in df.columns:
        raise ValueError("El Excel debe contener una columna 'Date'.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()
    df = df.sort_values("Date").set_index("Date")

    # Convertir precios a numerico (si algo raro -> NaN, sin inventar).
    tickers = [c for c in df.columns if c != "Date"]
    df[tickers] = df[tickers].apply(pd.to_numeric, errors="coerce")

    return df
