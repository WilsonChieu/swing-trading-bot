import pandas as pd
from unittest.mock import patch
from scripts.fetch_tickers import fetch_sp500_tickers, fetch_nasdaq100_tickers


@patch("scripts.fetch_tickers.pd.read_html")
def test_fetch_sp500_tickers_reads_symbol_column(mock_read_html):
    mock_read_html.return_value = [pd.DataFrame({"Symbol": ["AAPL", "MSFT", "BRK.B"]})]
    result = fetch_sp500_tickers()
    assert result == ["AAPL", "MSFT", "BRK-B"]


@patch("scripts.fetch_tickers.pd.read_html")
def test_fetch_nasdaq100_tickers_finds_ticker_table(mock_read_html):
    mock_read_html.return_value = [
        pd.DataFrame({"Company": ["Apple Inc."]}),
        pd.DataFrame({"Ticker": ["AAPL", "GOOGL"]}),
    ]
    result = fetch_nasdaq100_tickers()
    assert result == ["AAPL", "GOOGL"]


@patch("scripts.fetch_tickers.pd.read_html")
def test_fetch_nasdaq100_tickers_raises_if_no_ticker_column(mock_read_html):
    mock_read_html.return_value = [pd.DataFrame({"Company": ["Apple Inc."]})]
    import pytest
    with pytest.raises(ValueError):
        fetch_nasdaq100_tickers()
