from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest
import monitor_positions


def make_config():
    return MagicMock(
        alpaca_api_key="k", alpaca_secret_key="s", alpaca_base_url="url",
        discord_webhook_url="hook", supabase_url="url", supabase_service_key="key",
    )


def test_decide_exit_returns_target_when_profit_hits_threshold():
    assert monitor_positions.decide_exit(0.16, days_held=5) == "target"


def test_decide_exit_returns_stop_when_loss_hits_threshold():
    assert monitor_positions.decide_exit(-0.12, days_held=5) == "stop"


def test_decide_exit_returns_timeout_when_max_hold_exceeded():
    assert monitor_positions.decide_exit(0.02, days_held=28) == "timeout"


def test_decide_exit_returns_none_when_no_condition_met():
    assert monitor_positions.decide_exit(0.05, days_held=10) is None


@patch("monitor_positions.send_webhook")
def test_run_sells_position_hitting_target_and_records_history(mock_send_webhook):
    config = make_config()
    entry_date = (date.today() - timedelta(days=5)).isoformat()

    alpaca = MagicMock()
    alpaca.get_open_positions.return_value = [
        {"ticker": "AAPL", "qty": 10.0, "avg_entry_price": 150.0, "current_price": 175.0, "unrealized_plpc": 0.1667},
    ]
    alpaca.submit_market_sell.return_value = {
        "order_id": "1", "ticker": "AAPL", "filled_qty": 10.0,
        "filled_avg_price": 175.0, "status": "filled",
    }

    db = MagicMock()
    db.get_active_picks.return_value = [
        {"id": 1, "ticker": "AAPL", "entry_date": entry_date, "entry_price": 150.0, "qty": 10.0, "reasoning": "test"},
    ]

    monitor_positions.run(config=config, alpaca=alpaca, db=db)

    alpaca.submit_market_sell.assert_called_once_with("AAPL", 10.0)
    db.close_position.assert_called_once()
    mock_send_webhook.assert_called_once()


@patch("monitor_positions.send_webhook")
def test_run_holds_position_when_no_exit_condition_met(mock_send_webhook):
    config = make_config()
    entry_date = (date.today() - timedelta(days=5)).isoformat()

    alpaca = MagicMock()
    alpaca.get_open_positions.return_value = [
        {"ticker": "AAPL", "qty": 10.0, "avg_entry_price": 150.0, "current_price": 153.0, "unrealized_plpc": 0.02},
    ]

    db = MagicMock()
    db.get_active_picks.return_value = [
        {"id": 1, "ticker": "AAPL", "entry_date": entry_date, "entry_price": 150.0, "qty": 10.0, "reasoning": "test"},
    ]

    monitor_positions.run(config=config, alpaca=alpaca, db=db)

    alpaca.submit_market_sell.assert_not_called()
    db.close_position.assert_not_called()
    mock_send_webhook.assert_not_called()


@patch("monitor_positions.send_webhook")
def test_run_records_realized_pnl_from_actual_fill_not_unrealized_snapshot(mock_send_webhook):
    config = make_config()
    entry_date = (date.today() - timedelta(days=5)).isoformat()

    # unrealized_plpc (0.1667) deliberately differs from the actual fill-based
    # realized P&L: (174.0 - 150.0) / 150.0 == 0.16
    alpaca = MagicMock()
    alpaca.get_open_positions.return_value = [
        {"ticker": "AAPL", "qty": 10.0, "avg_entry_price": 150.0, "current_price": 175.0, "unrealized_plpc": 0.1667},
    ]
    alpaca.submit_market_sell.return_value = {
        "order_id": "1", "ticker": "AAPL", "filled_qty": 10.0,
        "filled_avg_price": 174.0, "status": "filled",
    }

    db = MagicMock()
    db.get_active_picks.return_value = [
        {"id": 1, "ticker": "AAPL", "entry_date": entry_date, "entry_price": 150.0, "qty": 10.0, "reasoning": "test"},
    ]

    monitor_positions.run(config=config, alpaca=alpaca, db=db)

    db.close_position.assert_called_once()
    close_args = db.close_position.call_args.args
    recorded = close_args[1]
    assert recorded["realized_pnl_pct"] == pytest.approx(0.16)
    assert recorded["realized_pnl_pct"] != pytest.approx(0.1667)
    assert recorded["exit_price"] == 174.0

    embed_call = mock_send_webhook.call_args
    embed = embed_call.args[1]
    field_value = embed["fields"][0]["value"]
    assert "16.0%" in field_value
    assert "16.7%" not in field_value
