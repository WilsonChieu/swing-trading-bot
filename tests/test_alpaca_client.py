import pytest
from unittest.mock import MagicMock, patch
from swingbot.alpaca_client import AlpacaClient


@patch("swingbot.alpaca_client.TradingClient")
def test_get_available_cash_returns_account_cash(mock_trading_client_cls):
    mock_client = MagicMock()
    mock_client.get_account.return_value = MagicMock(cash="12345.67")
    mock_trading_client_cls.return_value = mock_client

    client = AlpacaClient("key", "secret")
    assert client.get_available_cash() == 12345.67


@patch("swingbot.alpaca_client.TradingClient")
def test_is_market_open_returns_true_when_clock_says_open(mock_trading_client_cls):
    mock_client = MagicMock()
    mock_client.get_clock.return_value = MagicMock(is_open=True)
    mock_trading_client_cls.return_value = mock_client

    client = AlpacaClient("key", "secret")
    assert client.is_market_open() is True


@patch("swingbot.alpaca_client.TradingClient")
def test_is_market_open_returns_false_when_clock_says_closed(mock_trading_client_cls):
    mock_client = MagicMock()
    mock_client.get_clock.return_value = MagicMock(is_open=False)
    mock_trading_client_cls.return_value = mock_client

    client = AlpacaClient("key", "secret")
    assert client.is_market_open() is False


@patch("swingbot.alpaca_client.TradingClient")
def test_get_open_positions_returns_list_of_dicts(mock_trading_client_cls):
    mock_position = MagicMock(
        symbol="AAPL", qty="10", avg_entry_price="150.0",
        current_price="160.0", unrealized_plpc="0.0667",
    )
    mock_client = MagicMock()
    mock_client.get_all_positions.return_value = [mock_position]
    mock_trading_client_cls.return_value = mock_client

    client = AlpacaClient("key", "secret")
    positions = client.get_open_positions()

    assert positions == [{
        "ticker": "AAPL",
        "qty": 10.0,
        "avg_entry_price": 150.0,
        "current_price": 160.0,
        "unrealized_plpc": 0.0667,
    }]


@patch("swingbot.alpaca_client.TradingClient")
def test_submit_market_buy_waits_for_fill_and_returns_details(mock_trading_client_cls):
    mock_order = MagicMock(id="order-1")
    mock_filled_order = MagicMock(
        id="order-1", symbol="AAPL", status="filled",
        filled_qty="5", filled_avg_price="200.0",
    )
    mock_client = MagicMock()
    mock_client.submit_order.return_value = mock_order
    mock_client.get_order_by_id.return_value = mock_filled_order
    mock_trading_client_cls.return_value = mock_client

    client = AlpacaClient("key", "secret")
    result = client.submit_market_buy("AAPL", 1000.0)

    assert result == {
        "order_id": "order-1",
        "ticker": "AAPL",
        "filled_qty": 5.0,
        "filled_avg_price": 200.0,
        "status": "filled",
    }


@patch("swingbot.alpaca_client.TradingClient")
def test_submit_market_sell_waits_for_fill_and_returns_details(mock_trading_client_cls):
    mock_order = MagicMock(id="order-2")
    mock_filled_order = MagicMock(
        id="order-2", symbol="AAPL", status="filled",
        filled_qty="5", filled_avg_price="210.0",
    )
    mock_client = MagicMock()
    mock_client.submit_order.return_value = mock_order
    mock_client.get_order_by_id.return_value = mock_filled_order
    mock_trading_client_cls.return_value = mock_client

    client = AlpacaClient("key", "secret")
    result = client.submit_market_sell("AAPL", 5.0)

    assert result == {
        "order_id": "order-2",
        "ticker": "AAPL",
        "filled_qty": 5.0,
        "filled_avg_price": 210.0,
        "status": "filled",
    }


@patch("swingbot.alpaca_client.TradingClient")
def test_submit_market_buy_raises_timeout_if_never_filled(mock_trading_client_cls):
    mock_order = MagicMock(id="order-3")
    mock_pending_order = MagicMock(status="pending")
    mock_client = MagicMock()
    mock_client.submit_order.return_value = mock_order
    mock_client.get_order_by_id.return_value = mock_pending_order
    mock_trading_client_cls.return_value = mock_client

    client = AlpacaClient("key", "secret")
    with pytest.raises(TimeoutError):
        client.submit_market_buy("AAPL", 1000.0, max_attempts=2, delay_seconds=0)
