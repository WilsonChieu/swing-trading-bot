import numpy as np
import pandas as pd
from swingbot.screener import (
    compute_rsi,
    days_since_bullish_crossover,
    is_above_sma_uptrend,
    volume_ratio,
)


def test_compute_rsi_is_100_for_strictly_increasing_prices():
    close = pd.Series(range(1, 21), dtype=float)
    assert compute_rsi(close) == 100.0


def test_compute_rsi_is_between_0_and_100_for_mixed_prices():
    close = pd.Series([10, 11, 9, 12, 8, 13, 7, 14, 6, 15, 14, 16, 13, 17, 12, 18], dtype=float)
    result = compute_rsi(close)
    assert 0.0 <= result <= 100.0


def test_days_since_bullish_crossover_detects_recent_cross():
    macd = pd.Series([-2, -1, -0.5, 0.5, 1.0, 1.5])
    signal = pd.Series([-1, -1, -1, 0, 0.5, 1.0])
    assert days_since_bullish_crossover(macd, signal) == 3


def test_days_since_bullish_crossover_returns_none_when_no_cross():
    macd = pd.Series([-2, -1.5, -1])
    signal = pd.Series([0, 0, 0])
    assert days_since_bullish_crossover(macd, signal) is None


def test_is_above_sma_uptrend_true_for_rising_prices():
    close = pd.Series(np.linspace(1, 200, 200))
    assert is_above_sma_uptrend(close) is True


def test_is_above_sma_uptrend_false_for_falling_prices():
    close = pd.Series(np.linspace(200, 1, 200))
    assert is_above_sma_uptrend(close) is False


def test_volume_ratio_compares_latest_to_20_day_average():
    volume = pd.Series([1000] * 20 + [2000], dtype=float)
    assert volume_ratio(volume) == 2.0
