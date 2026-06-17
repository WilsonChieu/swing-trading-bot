import pandas as pd
import swingbot.screener as screener
from swingbot.screener import (
    ScreenResult,
    passes_fundamental_filters,
    score_ticker,
    rank_candidates,
)


def test_passes_fundamental_filters_true_for_healthy_stock():
    fundamentals = {"market_cap": 5_000_000_000, "trailing_pe": 22, "earnings_growth": 0.1}
    assert passes_fundamental_filters(fundamentals) is True


def test_passes_fundamental_filters_false_for_small_cap():
    fundamentals = {"market_cap": 500_000_000, "trailing_pe": 22, "earnings_growth": 0.1}
    assert passes_fundamental_filters(fundamentals) is False


def test_passes_fundamental_filters_false_for_negative_earnings_growth():
    fundamentals = {"market_cap": 5_000_000_000, "trailing_pe": 22, "earnings_growth": -0.05}
    assert passes_fundamental_filters(fundamentals) is False


def test_passes_fundamental_filters_false_for_extreme_pe():
    fundamentals = {"market_cap": 5_000_000_000, "trailing_pe": 50, "earnings_growth": 0.1}
    assert passes_fundamental_filters(fundamentals) is False


def test_score_ticker_returns_none_when_fundamentals_fail():
    price_history = pd.DataFrame({"Close": [1.0, 2.0, 3.0], "Volume": [100, 100, 100]})
    fundamentals = {"market_cap": 500_000_000, "trailing_pe": 22, "earnings_growth": 0.1}
    assert score_ticker("AAPL", price_history, fundamentals) is None


def test_score_ticker_combines_signals_and_fundamentals(monkeypatch):
    monkeypatch.setattr(screener, "compute_rsi", lambda close: 60.0)
    monkeypatch.setattr(screener, "compute_macd_bullish_crossover_days_ago", lambda close: 2)
    monkeypatch.setattr(screener, "is_above_sma_uptrend", lambda close: True)
    monkeypatch.setattr(screener, "volume_ratio", lambda volume: 2.0)

    price_history = pd.DataFrame({"Close": [1.0, 2.0, 3.0], "Volume": [100, 100, 100]})
    fundamentals = {"market_cap": 5_000_000_000, "trailing_pe": 20, "earnings_growth": 0.1}

    result = score_ticker("AAPL", price_history, fundamentals)

    assert result == ScreenResult(
        ticker="AAPL",
        score=4.0,
        reasoning=(
            "RSI 60, MACD bullish crossover 2 days ago, above 50/200-SMA uptrend, "
            "volume 2.0x 20-day avg. Earnings growth 10% YoY, P/E 20."
        ),
    )


def test_rank_candidates_sorts_descending_and_excludes_held():
    candidates = [
        ScreenResult(ticker="AAPL", score=2.0, reasoning="r1"),
        ScreenResult(ticker="MSFT", score=4.0, reasoning="r2"),
        ScreenResult(ticker="GOOGL", score=3.0, reasoning="r3"),
    ]
    result = rank_candidates(candidates, exclude={"GOOGL"})
    assert [r.ticker for r in result] == ["MSFT", "AAPL"]
