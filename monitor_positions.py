from datetime import date
from swingbot.config import load_config
from swingbot.alpaca_client import AlpacaClient
from swingbot.db import Database
from swingbot.discord_notify import send_webhook, build_position_closed_embed, build_error_embed

TARGET_PNL_PCT = 0.15
STOP_PNL_PCT = -0.10
MAX_HOLD_DAYS = 28


def decide_exit(unrealized_plpc: float, days_held: int):
    if unrealized_plpc >= TARGET_PNL_PCT:
        return "target"
    if unrealized_plpc <= STOP_PNL_PCT:
        return "stop"
    if days_held >= MAX_HOLD_DAYS:
        return "timeout"
    return None


def run(config=None, alpaca=None, db=None):
    config = config or load_config()
    alpaca = alpaca or AlpacaClient(config.alpaca_api_key, config.alpaca_secret_key)
    db = db or Database(config.supabase_url, config.supabase_service_key)

    active = db.get_active_picks()
    positions = {p["ticker"]: p for p in alpaca.get_open_positions()}
    today = date.today()

    for pick in active:
        position = positions.get(pick["ticker"])
        if position is None:
            continue

        entry_date = date.fromisoformat(pick["entry_date"])
        days_held = (today - entry_date).days
        exit_reason = decide_exit(position["unrealized_plpc"], days_held)
        if exit_reason is None:
            continue

        order = alpaca.submit_market_sell(pick["ticker"], position["qty"])
        realized_pnl_pct = (order["filled_avg_price"] - pick["entry_price"]) / pick["entry_price"]
        db.close_position(pick["id"], {
            "exit_date": today.isoformat(),
            "exit_price": order["filled_avg_price"],
            "realized_pnl_pct": realized_pnl_pct,
            "exit_reason": exit_reason,
        })
        send_webhook(config.discord_webhook_url, build_position_closed_embed({
            "ticker": pick["ticker"],
            "entry_price": pick["entry_price"],
            "exit_price": order["filled_avg_price"],
            "realized_pnl_pct": realized_pnl_pct,
            "exit_reason": exit_reason,
            "days_held": days_held,
        }))


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        cfg = load_config()
        send_webhook(cfg.discord_webhook_url, build_error_embed("monitor_positions", str(exc)))
        raise
