import datetime
from swingbot.config import load_config
from swingbot.tickers import load_tickers
from swingbot.data import get_price_history, get_fundamentals
from swingbot.screener import score_ticker, rank_candidates
from swingbot.alpaca_client import AlpacaClient
from swingbot.db import Database
from swingbot.discord_notify import send_webhook, build_picks_embed, build_summary_embed, build_error_embed

MAX_OPEN_POSITIONS = 6
PICKS_PER_WEEK = 3
CASH_BUFFER = 0.95


def run(config=None, alpaca=None, db=None, tickers=None):
    config = config or load_config()
    alpaca = alpaca or AlpacaClient(config.alpaca_api_key, config.alpaca_secret_key)
    db = db or Database(config.supabase_url, config.supabase_service_key)
    tickers = tickers if tickers is not None else load_tickers()

    active = db.get_active_picks()
    held_tickers = {p["ticker"] for p in active}
    free_slots = MAX_OPEN_POSITIONS - len(active)

    scored = []
    for ticker in tickers:
        try:
            history = get_price_history(ticker)
            fundamentals = get_fundamentals(ticker)
            result = score_ticker(ticker, history, fundamentals)
        except Exception:
            continue
        if result is not None:
            scored.append(result)

    ranked = rank_candidates(scored, held_tickers)

    if free_slots > 0:
        to_buy = ranked[: min(PICKS_PER_WEEK, free_slots)]
        skipped = []
    else:
        to_buy = []
        skipped = [{"ticker": r.ticker} for r in ranked[:PICKS_PER_WEEK]]

    bought = []
    if to_buy:
        cash = alpaca.get_available_cash() * CASH_BUFFER
        notional_each = cash / len(to_buy)
        for candidate in to_buy:
            order = alpaca.submit_market_buy(candidate.ticker, notional_each)
            entry_price = order["filled_avg_price"]
            pick = {
                "ticker": candidate.ticker,
                "entry_date": datetime.date.today().isoformat(),
                "entry_price": entry_price,
                "qty": order["filled_qty"],
                "reasoning": candidate.reasoning,
                "target_price": entry_price * 1.15,
                "stop_price": entry_price * 0.90,
            }
            db.insert_active_pick(pick)
            bought.append(pick)

    send_webhook(config.discord_webhook_url, build_picks_embed(bought, skipped))

    remaining = db.get_active_picks()
    history_summary = db.get_trade_history_summary()
    summary_embed = build_summary_embed({
        "open_positions": len(remaining),
        "equity": alpaca.get_available_cash(),
        "total_realized_pnl_pct": history_summary["total_realized_pnl_pct"],
    })
    send_webhook(config.discord_webhook_url, summary_embed)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        cfg = load_config()
        send_webhook(cfg.discord_webhook_url, build_error_embed("screen_and_buy", str(exc)))
        raise
