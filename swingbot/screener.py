import pandas as pd


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
