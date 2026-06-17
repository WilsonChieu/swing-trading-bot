import pandas as pd
from dataclasses import dataclass


@dataclass
class ScreenResult:
    ticker: str
    score: float
    reasoning: str


def compute_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd_and_signal(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def days_since_bullish_crossover(macd: pd.Series, signal: pd.Series) -> int | None:
    diff = macd - signal
    crossed = (diff > 0) & (diff.shift(1) <= 0)
    crossover_positions = [i for i, crossed_here in enumerate(crossed) if crossed_here]
    if not crossover_positions:
        return None
    last_crossover_index = crossover_positions[-1]
    return (len(macd) - 1) - last_crossover_index


def compute_macd_bullish_crossover_days_ago(close: pd.Series) -> int | None:
    macd, signal = _macd_and_signal(close)
    return days_since_bullish_crossover(macd, signal)


def is_above_sma_uptrend(close: pd.Series) -> bool:
    sma50 = close.rolling(50).mean().iloc[-1]
    sma200 = close.rolling(200).mean().iloc[-1]
    price = close.iloc[-1]
    return bool(price > sma50 and price > sma200)


def volume_ratio(volume: pd.Series, period: int = 20) -> float:
    recent_avg = volume.iloc[-period - 1 : -1].mean()
    latest = volume.iloc[-1]
    return float(latest / recent_avg) if recent_avg else 0.0


def passes_fundamental_filters(fundamentals: dict) -> bool:
    market_cap = fundamentals.get("market_cap")
    pe = fundamentals.get("trailing_pe")
    earnings_growth = fundamentals.get("earnings_growth")

    if market_cap is None or market_cap < 2_000_000_000:
        return False
    if earnings_growth is None or earnings_growth <= 0:
        return False
    if pe is None or not (5 <= pe <= 40):
        return False
    return True


def score_ticker(ticker: str, price_history: pd.DataFrame, fundamentals: dict) -> "ScreenResult | None":
    if not passes_fundamental_filters(fundamentals):
        return None

    close = price_history["Close"]
    volume = price_history["Volume"]

    rsi = compute_rsi(close)
    crossover_days = compute_macd_bullish_crossover_days_ago(close)
    uptrend = is_above_sma_uptrend(close)
    vol_ratio = volume_ratio(volume)

    rsi_score = 1.0 if 50 <= rsi <= 70 else 0.0
    macd_score = 1.0 if crossover_days is not None and crossover_days <= 5 else 0.0
    uptrend_score = 1.0 if uptrend else 0.0
    volume_score = 1.0 if vol_ratio >= 1.5 else 0.0
    total_score = rsi_score + macd_score + uptrend_score + volume_score

    reasoning = (
        f"RSI {rsi:.0f}, "
        f"MACD bullish crossover {crossover_days if crossover_days is not None else 'none'} days ago, "
        f"{'above' if uptrend else 'below'} 50/200-SMA uptrend, "
        f"volume {vol_ratio:.1f}x 20-day avg. "
        f"Earnings growth {fundamentals['earnings_growth'] * 100:.0f}% YoY, P/E {fundamentals['trailing_pe']:.0f}."
    )
    return ScreenResult(ticker=ticker, score=total_score, reasoning=reasoning)


def rank_candidates(scored: list, exclude: set) -> list:
    filtered = [r for r in scored if r.ticker not in exclude]
    return sorted(filtered, key=lambda r: r.score, reverse=True)
