import pandas as pd
from unittest.mock import patch, MagicMock
from swingbot.data import get_price_history, get_fundamentals


@patch("swingbot.data.yf.Ticker")
def test_get_price_history_returns_history_dataframe(mock_ticker_cls):
    expected_df = pd.DataFrame({"Close": [100, 101], "Volume": [1000, 1100]})
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = expected_df
    mock_ticker_cls.return_value = mock_ticker

    result = get_price_history("AAPL")

    mock_ticker_cls.assert_called_once_with("AAPL")
    mock_ticker.history.assert_called_once_with(period="1y")
    assert result is expected_df


@patch("swingbot.data.yf.Ticker")
def test_get_fundamentals_extracts_known_fields(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "marketCap": 5_000_000_000,
        "trailingPE": 22.5,
        "earningsQuarterlyGrowth": 0.14,
        "irrelevantField": "ignored",
    }
    mock_ticker_cls.return_value = mock_ticker

    result = get_fundamentals("AAPL")

    assert result == {
        "market_cap": 5_000_000_000,
        "trailing_pe": 22.5,
        "earnings_growth": 0.14,
    }
