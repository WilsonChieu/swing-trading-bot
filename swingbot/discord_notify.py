import requests

EXIT_REASON_TITLES = {
    "target": "Target Hit",
    "stop": "Stop Hit",
    "timeout": "Max Hold Exit",
}


def send_webhook(webhook_url: str, embed: dict) -> None:
    response = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    response.raise_for_status()


def build_picks_embed(bought: list, skipped: list) -> dict:
    fields = [
        {
            "name": pick["ticker"],
            "value": (
                f"Entry: ${pick['entry_price']:.2f} x {pick['qty']:.2f} shares\n"
                f"{pick['reasoning']}\n"
                f"Target: ${pick['target_price']:.2f} / Stop: ${pick['stop_price']:.2f}"
            ),
        }
        for pick in bought
    ]
    if skipped:
        skipped_names = ", ".join(s["ticker"] for s in skipped)
        fields.append({"name": "Skipped (no free slots)", "value": skipped_names})
    return {"title": "Monday Swing Picks", "fields": fields}


def build_position_closed_embed(trade: dict) -> dict:
    title = EXIT_REASON_TITLES.get(trade["exit_reason"], "Position Closed")
    value = (
        f"Entry ${trade['entry_price']:.2f} -> Exit ${trade['exit_price']:.2f}\n"
        f"P&L: {trade['realized_pnl_pct'] * 100:.1f}%\n"
        f"Held {trade['days_held']} days"
    )
    return {"title": title, "fields": [{"name": trade["ticker"], "value": value}]}


def build_summary_embed(summary: dict) -> dict:
    value = (
        f"Open positions: {summary['open_positions']}\n"
        f"Account equity: ${summary['equity']:.2f}\n"
        f"Total realized P&L: {summary['total_realized_pnl_pct'] * 100:.1f}%"
    )
    return {"title": "Weekly Portfolio Summary", "fields": [{"name": "Status", "value": value}]}


def build_error_embed(job_name: str, error_message: str) -> dict:
    return {"title": "SwingBot Error", "fields": [{"name": job_name, "value": error_message}]}


def build_market_closed_embed() -> dict:
    return {
        "title": "Market Closed",
        "fields": [{"name": "Status", "value": "Market is closed; skipping this screen-and-buy run."}],
    }
