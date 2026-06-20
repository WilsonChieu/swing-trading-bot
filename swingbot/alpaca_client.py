import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


class AlpacaClient:
    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self._client = TradingClient(api_key, secret_key, paper=paper)

    def get_available_cash(self) -> float:
        account = self._client.get_account()
        return float(account.cash)

    def is_market_open(self) -> bool:
        return bool(self._client.get_clock().is_open)

    def get_open_positions(self) -> list:
        positions = self._client.get_all_positions()
        return [
            {
                "ticker": p.symbol,
                "qty": float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "unrealized_plpc": float(p.unrealized_plpc),
            }
            for p in positions
        ]

    def submit_market_buy(self, ticker: str, notional: float, max_attempts: int = 10, delay_seconds: float = 1.0) -> dict:
        order = self._client.submit_order(MarketOrderRequest(
            symbol=ticker,
            notional=round(notional, 2),
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        ))
        return self._wait_for_fill(order.id, max_attempts, delay_seconds)

    def submit_market_sell(self, ticker: str, qty: float, max_attempts: int = 10, delay_seconds: float = 1.0) -> dict:
        order = self._client.submit_order(MarketOrderRequest(
            symbol=ticker,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        ))
        return self._wait_for_fill(order.id, max_attempts, delay_seconds)

    def _wait_for_fill(self, order_id, max_attempts: int, delay_seconds: float) -> dict:
        for _ in range(max_attempts):
            order = self._client.get_order_by_id(order_id)
            if order.status == "filled":
                return {
                    "order_id": str(order.id),
                    "ticker": order.symbol,
                    "filled_qty": float(order.filled_qty),
                    "filled_avg_price": float(order.filled_avg_price),
                    "status": order.status,
                }
            time.sleep(delay_seconds)
        raise TimeoutError(f"Order {order_id} did not fill within {max_attempts * delay_seconds}s")
