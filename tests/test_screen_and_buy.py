# tests/test_screen_and_buy.py
from unittest.mock import MagicMock, patch
from swingbot.screener import ScreenResult
from swingbot import screen_and_buy


def make_config():
    return MagicMock(
        alpaca_api_key="k", alpaca_secret_key="s", alpaca_base_url="url",
        discord_webhook_url="hook", supabase_url="url", supabase_service_key="key",
    )


@patch("swingbot.screen_and_buy.send_webhook")
@patch("swingbot.screen_and_buy.get_fundamentals")
@patch("swingbot.screen_and_buy.get_price_history")
@patch("swingbot.screen_and_buy.score_ticker")
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


@patch("swingbot.screen_and_buy.send_webhook")
@patch("swingbot.screen_and_buy.get_fundamentals")
@patch("swingbot.screen_and_buy.get_price_history")
@patch("swingbot.screen_and_buy.score_ticker")
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
