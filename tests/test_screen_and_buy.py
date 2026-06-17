# tests/test_screen_and_buy.py
from unittest.mock import MagicMock, patch
from swingbot.screener import ScreenResult
import screen_and_buy


def make_config():
    return MagicMock(
        alpaca_api_key="k", alpaca_secret_key="s", alpaca_base_url="url",
        discord_webhook_url="hook", supabase_url="url", supabase_service_key="key",
    )


@patch("screen_and_buy.send_webhook")
@patch("screen_and_buy.get_fundamentals")
@patch("screen_and_buy.get_price_history")
@patch("screen_and_buy.score_ticker")
def test_run_buys_top_picks_and_records_them(
    mock_score_ticker, mock_get_price_history, mock_get_fundamentals, mock_send_webhook,
):
    mock_get_price_history.return_value = "history"
    mock_get_fundamentals.return_value = {"market_cap": 5_000_000_000}
    mock_score_ticker.side_effect = lambda ticker, history, fundamentals: ScreenResult(
        ticker=ticker, score=1.0, reasoning=f"reasoning for {ticker}",
    )

    config = make_config()
    alpaca = MagicMock()
    alpaca.get_available_cash.return_value = 10000.0
    alpaca.submit_market_buy.side_effect = lambda ticker, notional: {
        "order_id": "1", "ticker": ticker, "filled_qty": 10.0,
        "filled_avg_price": 100.0, "status": "filled",
    }
    db = MagicMock()
    db.get_active_picks.return_value = []
    db.get_trade_history_summary.return_value = {"closed_trades": 0, "total_realized_pnl_pct": 0.0}

    screen_and_buy.run(config=config, alpaca=alpaca, db=db, tickers=["AAPL", "MSFT"])

    assert alpaca.submit_market_buy.call_count == 2
    assert db.insert_active_pick.call_count == 2
    assert mock_send_webhook.call_count == 2


@patch("screen_and_buy.send_webhook")
@patch("screen_and_buy.get_fundamentals")
@patch("screen_and_buy.get_price_history")
@patch("screen_and_buy.score_ticker")
def test_run_skips_buying_when_no_free_slots(
    mock_score_ticker, mock_get_price_history, mock_get_fundamentals, mock_send_webhook,
):
    mock_get_price_history.return_value = "history"
    mock_get_fundamentals.return_value = {"market_cap": 5_000_000_000}
    mock_score_ticker.side_effect = lambda ticker, history, fundamentals: ScreenResult(
        ticker=ticker, score=1.0, reasoning=f"reasoning for {ticker}",
    )

    config = make_config()
    alpaca = MagicMock()
    alpaca.get_available_cash.return_value = 5000.0
    db = MagicMock()
    db.get_active_picks.return_value = [{"ticker": f"HELD{i}"} for i in range(6)]
    db.get_trade_history_summary.return_value = {"closed_trades": 0, "total_realized_pnl_pct": 0.0}

    screen_and_buy.run(config=config, alpaca=alpaca, db=db, tickers=["AAPL"])

    alpaca.submit_market_buy.assert_not_called()
    db.insert_active_pick.assert_not_called()


@patch("screen_and_buy.time.sleep")
@patch("screen_and_buy.score_ticker")
@patch("screen_and_buy.get_fundamentals")
@patch("screen_and_buy.get_price_history")
def test_fetch_and_score_retries_once_then_succeeds(
    mock_get_price_history, mock_get_fundamentals, mock_score_ticker, mock_sleep,
):
    mock_get_price_history.side_effect = [Exception("boom"), "history"]
    mock_get_fundamentals.return_value = {"market_cap": 5_000_000_000}
    mock_score_ticker.return_value = ScreenResult(
        ticker="AAPL", score=1.0, reasoning="reasoning for AAPL",
    )

    result = screen_and_buy._fetch_and_score("AAPL")

    assert result is not None
    assert result.ticker == "AAPL"
    assert mock_get_price_history.call_count == 2
    mock_sleep.assert_called_once()


@patch("screen_and_buy.time.sleep")
@patch("screen_and_buy.score_ticker")
@patch("screen_and_buy.get_fundamentals")
@patch("screen_and_buy.get_price_history")
def test_fetch_and_score_returns_none_after_exhausting_retries(
    mock_get_price_history, mock_get_fundamentals, mock_score_ticker, mock_sleep,
):
    mock_get_price_history.side_effect = Exception("always fails")

    result = screen_and_buy._fetch_and_score("AAPL")

    assert result is None
    assert mock_get_price_history.call_count == 2
    mock_score_ticker.assert_not_called()


@patch("screen_and_buy.send_webhook")
@patch("screen_and_buy.get_fundamentals")
@patch("screen_and_buy.get_price_history")
@patch("screen_and_buy.score_ticker")
def test_run_alerts_and_continues_when_insert_active_pick_fails(
    mock_score_ticker, mock_get_price_history, mock_get_fundamentals, mock_send_webhook,
):
    mock_get_price_history.return_value = "history"
    mock_get_fundamentals.return_value = {"market_cap": 5_000_000_000}
    mock_score_ticker.side_effect = lambda ticker, history, fundamentals: ScreenResult(
        ticker=ticker, score=1.0, reasoning=f"reasoning for {ticker}",
    )

    config = make_config()
    alpaca = MagicMock()
    alpaca.get_available_cash.return_value = 10000.0
    alpaca.submit_market_buy.side_effect = lambda ticker, notional: {
        "order_id": "1", "ticker": ticker, "filled_qty": 10.0,
        "filled_avg_price": 100.0, "status": "filled",
    }
    db = MagicMock()
    db.get_active_picks.return_value = []
    db.get_trade_history_summary.return_value = {"closed_trades": 0, "total_realized_pnl_pct": 0.0}
    db.insert_active_pick.side_effect = [Exception("supabase down"), None]

    screen_and_buy.run(config=config, alpaca=alpaca, db=db, tickers=["AAPL", "MSFT"])

    assert alpaca.submit_market_buy.call_count == 2
    assert db.insert_active_pick.call_count == 2

    error_calls = [
        call for call in mock_send_webhook.call_args_list
        if "AAPL" in str(call) and "Supabase" in str(call)
    ]
    assert len(error_calls) == 1

    # The picks embed (sent right after the buy loop) should only list MSFT,
    # since AAPL's insert_active_pick failed and was excluded from `bought`.
    picks_embed_call = mock_send_webhook.call_args_list[1]
    picks_embed = picks_embed_call.args[1]
    bought_tickers = [field["name"] for field in picks_embed["fields"]]
    assert bought_tickers == ["MSFT"]
