from unittest.mock import patch, MagicMock
from swingbot.discord_notify import (
    send_webhook,
    build_picks_embed,
    build_position_closed_embed,
    build_summary_embed,
    build_error_embed,
)


@patch("swingbot.discord_notify.requests.post")
def test_send_webhook_posts_embed(mock_post):
    mock_post.return_value = MagicMock(raise_for_status=lambda: None)
    send_webhook("https://discord.example/webhook", {"title": "Test"})
    mock_post.assert_called_once_with(
        "https://discord.example/webhook",
        json={"embeds": [{"title": "Test"}]},
        timeout=10,
    )


def test_build_picks_embed_includes_bought_and_skipped():
    bought = [{
        "ticker": "AAPL", "entry_price": 150.0, "qty": 3.33,
        "reasoning": "strong momentum", "target_price": 172.5, "stop_price": 135.0,
    }]
    skipped = [{"ticker": "MSFT"}]

    embed = build_picks_embed(bought, skipped)

    assert embed["title"] == "Monday Swing Picks"
    assert embed["fields"][0]["name"] == "AAPL"
    assert "strong momentum" in embed["fields"][0]["value"]
    assert embed["fields"][1]["name"] == "Skipped (no free slots)"
    assert "MSFT" in embed["fields"][1]["value"]


def test_build_position_closed_embed_labels_target_hit():
    trade = {
        "ticker": "AAPL", "entry_price": 150.0, "exit_price": 172.5,
        "realized_pnl_pct": 0.15, "exit_reason": "target", "days_held": 10,
    }
    embed = build_position_closed_embed(trade)
    assert embed["title"] == "Target Hit"
    assert "15.0%" in embed["fields"][0]["value"]


def test_build_summary_embed_formats_fields():
    summary = {"open_positions": 2, "equity": 98000.0, "total_realized_pnl_pct": 0.05}
    embed = build_summary_embed(summary)
    assert embed["title"] == "Weekly Portfolio Summary"
    assert "Open positions: 2" in embed["fields"][0]["value"]


def test_build_error_embed_includes_job_name_and_message():
    embed = build_error_embed("screen_and_buy", "yfinance timeout")
    assert embed["title"] == "SwingBot Error"
    assert embed["fields"][0]["name"] == "screen_and_buy"
    assert "yfinance timeout" in embed["fields"][0]["value"]
