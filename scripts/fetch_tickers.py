import pandas as pd

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
OUTPUT_PATH = "data/sp500_nasdaq100_tickers.csv"


def fetch_sp500_tickers() -> list[str]:
    tables = pd.read_html(SP500_URL)
    df = tables[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()


def fetch_nasdaq100_tickers() -> list[str]:
    tables = pd.read_html(NASDAQ100_URL)
    for table in tables:
        if "Ticker" in table.columns:
            return table["Ticker"].tolist()
    raise ValueError("Could not find Nasdaq-100 ticker table")


def main():
    tickers = sorted(set(fetch_sp500_tickers()) | set(fetch_nasdaq100_tickers()))
    with open(OUTPUT_PATH, "w", newline="") as f:
        f.write("ticker\n")
        for ticker in tickers:
            f.write(f"{ticker}\n")
    print(f"Wrote {len(tickers)} tickers to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
