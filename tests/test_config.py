import pytest
from swingbot.config import load_config


def test_load_config_reads_from_environment(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "key123")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret123")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "supabase-key")
    monkeypatch.delenv("ALPACA_BASE_URL", raising=False)

    config = load_config()

    assert config.alpaca_api_key == "key123"
    assert config.alpaca_secret_key == "secret123"
    assert config.alpaca_base_url == "https://paper-api.alpaca.markets"
    assert config.discord_webhook_url == "https://discord.example/webhook"
    assert config.supabase_url == "https://example.supabase.co"
    assert config.supabase_service_key == "supabase-key"


def test_load_config_raises_when_required_var_missing(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    with pytest.raises(KeyError):
        load_config()
