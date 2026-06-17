import yfinance as yf
import pandas as pd


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)


def get_fundamentals(ticker: str) -> dict:
    info = yf.Ticker(ticker).info
    return {
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "earnings_growth": info.get("earningsQuarterlyGrowth"),
    }
