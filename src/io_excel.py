from pathlib import Path
import pandas as pd

def read_prices_excel(path: str) -> pd.DataFrame:
    """
    Formato esperado (tu Excel):
      - columna 'Date'
      - resto columnas: tickers (35) con precios float
    Devuelve DataFrame indexado por fecha (datetime), columnas=tickers.
    """
    df = pd.read_excel(path)

    if "Date" not in df.columns:
        raise ValueError("El Excel debe contener una columna 'Date'.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()
    df = df.sort_values("Date").set_index("Date")

    # Convertir precios a numérico (si algo raro -> NaN, sin inventar)
    tickers = [c for c in df.columns if c != "Date"]
    df[tickers] = df[tickers].apply(pd.to_numeric, errors="coerce")

    return df

def export_results(df: pd.DataFrame, out_path: str) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out, index=True)

