# Swing Trading Bot — Design Spec

## Goal

A bot that, every Monday, screens the S&P 500 + Nasdaq 100 for swing-trade
candidates, buys the top picks in an Alpaca **paper** trading account,
targets 15-20% profit per trade, and notifies a Discord channel with picks
and reasoning. A daily job monitors open positions and exits them on
target/stop/timeout, also notifying Discord.

This is a paper-trading (simulated money) system for now — not connected to
a real brokerage account.

## Non-Goals

- Real-money trading (Alpaca paper only)
- Intraday/day trading (this is swing trading: holds of days to weeks)
- A web dashboard or UI (Discord notifications + Supabase tables are the
  only interfaces)
- Automatic reconciliation if Alpaca and Supabase state ever diverge
  (logged loudly, not auto-fixed)

## Architecture

```
                    +------------------+
  Monday 10:35 ET   | screen_and_buy.py|--reads tickers--> S&P500+Nasdaq100 list (static CSV in repo)
  (GitHub Actions)  +--------+---------+
                              | yfinance: price history + fundamentals
                              v
                     screener.py (scoring/ranking)
                              | top 3 not already held
                              v
                     alpaca_client.py (buy orders, paper)
                              |                       |
                              v                       v
                     Supabase: active_picks      Discord: "Monday Picks" embed
                     table (insert)               (ticker, reasoning, entry price)

  Weekdays 16:30 ET  +-------------------+
  (GitHub Actions)   | monitor_positions.py |--reads--> Alpaca open positions (live P&L%)
                     +--------+----------+           Supabase active_picks (entry_date, reasoning)
                              | evaluate: +15-20% / -10% / 4wk
                              v
                     alpaca_client.py (sell orders)
                              |
                              v
                     Supabase: move row active_picks -> trade_history
                              |
                              v
                     Discord: "Position Closed" embed (P&L, reason)
```

Alpaca's paper account is the system of record for cash, open positions,
and fills. Supabase stores the metadata Alpaca doesn't track: why a stock
was picked, and historical closed-trade records.

## Components

All in one Python package, `swingbot/`:

- `tickers.py` — static list of S&P 500 + Nasdaq 100 symbols (CSV checked
  into the repo)
- `data.py` — yfinance wrappers: fetch price history (for technicals) and
  fundamentals (P/E, EPS growth, market cap) per ticker
- `screener.py` — computes technical signals (RSI, MACD, SMA50/200
  crossover, volume vs 20-day avg) + fundamental filters, combines into a
  composite score, returns ranked candidates with human-readable reasoning
  strings
- `alpaca_client.py` — thin wrapper around the `alpaca-py` SDK: get account
  cash, get open positions, submit market buy/sell orders (paper
  environment)
- `db.py` — Supabase client: CRUD for `active_picks` and `trade_history`
  tables
- `discord_notify.py` — builds and posts Discord embeds (picks, exits,
  summary, errors) via webhook
- `screen_and_buy.py` — Monday entrypoint, wires the above together
- `monitor_positions.py` — daily entrypoint, wires the above together
- `config.py` — reads secrets/env vars (Alpaca keys, Discord webhook,
  Supabase URL/key, thresholds)

## Screening Logic

Computed per ticker from yfinance daily data:

**Technical signals** (each normalized 0-1, summed into a composite score):
- RSI(14) in the 50-70 band (momentum without being overbought)
- MACD bullish crossover within the last 5 trading days
- Price above both the 50-day and 200-day SMA (uptrend)
- Latest day's volume ≥ 1.5x the 20-day average volume (breakout
  confirmation)

**Fundamental filters** (pass/fail — a ticker failing any of these is
excluded before scoring):
- Market cap ≥ $2B (avoid micro-caps)
- Positive trailing EPS growth
- P/E between 5 and 40 (excludes unprofitable or extreme-valuation names)

**Reasoning string** — generated from the actual computed values, e.g.:
`"RSI 58 (healthy momentum), MACD bullish crossover 2 days ago, price above
50/200-SMA uptrend, volume 1.8x 20-day avg. EPS growth +14% YoY, P/E 22."`

## Trading Rules

**Buy logic** (`screen_and_buy.py`, runs Mondays):
1. Score all ~600 tickers, rank descending by composite score, drop any
   ticker already present in `active_picks`
2. Take the top 3 by score; if fewer than 3 free slots remain (max 6
   concurrent positions), buy only that many
3. If 0 slots are free, skip buying — still send a Discord notice listing
   the top candidates that would have been bought
4. Read available cash from Alpaca, use 95% of it (buffer for
   slippage/fees), split equally across the picks being bought this run,
   submit market buy orders
5. Insert one row per buy into Supabase `active_picks`: ticker, entry_date,
   entry_price, qty, reasoning, target_price (entry × 1.15), stop_price
   (entry × 0.90)

**Sell logic** (`monitor_positions.py`, runs every weekday after close):
For each row in `active_picks`, fetch the live Alpaca position for that
ticker and compute unrealized P&L%:
- P&L% ≥ +15% → sell, exit_reason = `target`
- P&L% ≤ -10% → sell, exit_reason = `stop`
- `today - entry_date` ≥ 28 days → sell, exit_reason = `timeout`
- Otherwise → hold, no action

On sell: submit a market sell order, move the row from `active_picks` to
`trade_history` (adding exit_date, exit_price, realized_pnl_pct,
exit_reason), send a Discord "Position Closed" embed.

## Database Schema (Supabase / Postgres)

```sql
create table active_picks (
  id bigint generated always as identity primary key,
  ticker text not null,
  entry_date date not null,
  entry_price numeric not null,
  qty numeric not null,
  reasoning text not null,
  target_price numeric not null,
  stop_price numeric not null,
  created_at timestamptz default now()
);

create table trade_history (
  id bigint generated always as identity primary key,
  ticker text not null,
  entry_date date not null,
  entry_price numeric not null,
  exit_date date not null,
  exit_price numeric not null,
  qty numeric not null,
  reasoning text not null,
  realized_pnl_pct numeric not null,
  exit_reason text not null check (exit_reason in ('target', 'stop', 'timeout')),
  created_at timestamptz default now()
);
```

No RLS policies — only the bot, via a service-role key that is never
exposed to a client, touches these tables.

## Discord Notifications

All sent as rich embeds via a single webhook URL:

1. **Monday Picks** — title "Monday Swing Picks", one field per bought
   ticker (entry price, qty, reasoning, target/stop), plus a note on any
   top candidates skipped due to no free slots
2. **Position Closed** — title varies by exit_reason ("Target Hit" / "Stop
   Hit" / "Max Hold Exit"), shows ticker, entry→exit price, realized P&L%,
   days held
3. **Weekly Portfolio Summary** — sent alongside #1 each Monday: current
   open position count, total paper account equity, total realized P&L to
   date (sum from `trade_history`)
4. **Error Alert** — title "SwingBot Error", job name, exception message —
   sent whenever `screen_and_buy.py` or `monitor_positions.py` raises an
   unhandled exception

## Scheduling

GitHub Actions workflows in `.github/workflows/`:

- `monday-screen-buy.yml` — cron `35 14 * * 1` (10:35am ET / 14:35 UTC on
  Mondays), runs `screen_and_buy.py`
- `daily-monitor.yml` — cron `30 21 * * 1-5` (4:30pm ET / 21:30 UTC on
  weekdays), runs `monitor_positions.py`

Both install `requirements.txt` and inject secrets as environment
variables.

## Error Handling

- Each entrypoint (`screen_and_buy.py`, `monitor_positions.py`) wraps its
  main logic in try/except; on exception it posts the Error Alert embed to
  Discord and re-raises, so the GitHub Actions run also shows as failed
- yfinance/Alpaca network calls get a single retry with backoff before
  being treated as a failure for that specific ticker (skip that ticker,
  don't abort the whole run)
- Supabase writes happen as the last step of each buy/sell action — if the
  Alpaca order succeeds but the Supabase write fails, this mismatch is
  logged and alerted loudly via the Error Alert embed; no automatic
  reconciliation is attempted (out of scope)

## Testing Strategy

- Unit tests (`pytest`) for `screener.py` scoring math using fixed
  synthetic price/fundamental data (no network calls)
- Unit tests for the buy/sell decision logic in `screen_and_buy.py` /
  `monitor_positions.py` with mocked Alpaca/Supabase/Discord clients
- No live integration tests against real Alpaca/Discord run in CI (would
  require live secrets in PR runs); manual end-to-end verification against
  the paper account is the final task of the implementation plan

## One-Time Setup

1. Create an Alpaca paper-trading account, generate an API key/secret
2. Create a Discord server channel and a webhook URL for it
3. Create a Supabase project, run the schema SQL above
4. Create a GitHub repo for this project, push the code, add repo secrets:
   `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `DISCORD_WEBHOOK_URL`,
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`

## Key Decisions Log

- **Scope**: fully automated paper trading (not alert-only), per user
  request — Alpaca paper environment only, no real money
- **Strategy**: technical + fundamental composite scoring
- **Data source**: yfinance (free, no key) for both price history and
  fundamentals
- **Universe**: S&P 500 + Nasdaq 100 (~600 tickers)
- **Position sizing**: top 3 picks per week, splitting available cash
  equally; max 6 concurrent open positions
- **Exit strategy**: daily monitoring job (not bracket orders) — checked
  once daily after market close
- **Risk rules**: +15% target / -10% stop / 28-day max hold
- **Hosting**: GitHub Actions scheduled workflows (free, no server to
  maintain)
- **State**: Alpaca is the source of truth for cash/positions/fills;
  Supabase stores pick reasoning and historical trade records
