from unittest.mock import MagicMock, patch
from swingbot.db import Database


@patch("swingbot.db.create_client")
def test_get_active_picks_returns_rows(mock_create_client):
    mock_response = MagicMock(data=[{"id": 1, "ticker": "AAPL"}])
    mock_table = MagicMock()
    mock_table.select.return_value.execute.return_value = mock_response
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_create_client.return_value = mock_client

    db = Database("url", "key")
    result = db.get_active_picks()

    assert result == [{"id": 1, "ticker": "AAPL"}]
    mock_client.table.assert_called_with("active_picks")


@patch("swingbot.db.create_client")
def test_insert_active_pick_inserts_row(mock_create_client):
    mock_table = MagicMock()
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_create_client.return_value = mock_client

    db = Database("url", "key")
    db.insert_active_pick({"ticker": "AAPL"})

    mock_table.insert.assert_called_with({"ticker": "AAPL"})
    mock_table.insert.return_value.execute.assert_called_once()


@patch("swingbot.db.create_client")
def test_close_position_moves_row_to_trade_history(mock_create_client):
    pick_row = {
        "id": 1,
        "ticker": "AAPL",
        "entry_date": "2026-06-01",
        "entry_price": 150.0,
        "qty": 5.0,
        "reasoning": "test reasoning",
    }
    mock_select_response = MagicMock(data=pick_row)
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_select_response
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_create_client.return_value = mock_client

    db = Database("url", "key")
    db.close_position(1, {
        "exit_date": "2026-06-10",
        "exit_price": 172.5,
        "realized_pnl_pct": 0.15,
        "exit_reason": "target",
    })

    mock_table.insert.assert_called_with({
        "ticker": "AAPL",
        "entry_date": "2026-06-01",
        "entry_price": 150.0,
        "qty": 5.0,
        "reasoning": "test reasoning",
        "exit_date": "2026-06-10",
        "exit_price": 172.5,
        "realized_pnl_pct": 0.15,
        "exit_reason": "target",
    })
    mock_table.delete.return_value.eq.assert_called_with("id", 1)


@patch("swingbot.db.create_client")
def test_get_trade_history_summary_sums_pnl(mock_create_client):
    mock_response = MagicMock(data=[{"realized_pnl_pct": 0.15}, {"realized_pnl_pct": -0.05}])
    mock_table = MagicMock()
    mock_table.select.return_value.execute.return_value = mock_response
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_create_client.return_value = mock_client

    db = Database("url", "key")
    summary = db.get_trade_history_summary()

    assert summary == {"closed_trades": 2, "total_realized_pnl_pct": 0.10}
