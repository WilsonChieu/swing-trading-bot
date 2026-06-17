import csv
from pathlib import Path

DEFAULT_TICKERS_CSV_PATH = Path(__file__).parent.parent / "data" / "sp500_nasdaq100_tickers.csv"


def load_tickers(csv_path: Path = DEFAULT_TICKERS_CSV_PATH) -> list[str]:
    with open(csv_path, newline="") as f:
        rows = list(csv.reader(f))
    return [row[0].strip() for row in rows[1:] if row and row[0].strip()]
