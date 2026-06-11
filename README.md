# Crypto Trader

An automated crypto trading bot built on [Freqtrade](https://www.freqtrade.io/),
currently running in **dry-run (paper trading) mode only** — it trades fake money
against live market prices. No real funds are at risk.

## Honest expectations

There is no bot that reliably makes "crazy profit" every day. The goals here are:

1. Learn how algorithmic trading actually works.
2. Build, backtest, and paper-trade strategies with real market data.
3. Only ever consider real money after weeks of validated dry-run results,
   and only with money you are fully prepared to lose.

## Project layout

- `config.json` — bot configuration (dry-run mode, Binance market data, USDT pairs)
- `user_data/strategies/TrendFollowStrategy.py` — EMA-crossover trend follower (4h)
- `user_data/strategies/MeanReversionStrategy.py` — Bollinger/RSI dip buyer (1h)
- `user_data/data/` — downloaded historical candle data
- `dashboard/` — read-only dashboard website (FastAPI + static page)
- `docker-compose.yml` + `config.docker.json` — one-command 24/7 deployment (see `DEPLOY.md`)
- `start-bot.ps1` — starts bot + website; runs automatically at Windows logon
  (via `CryptoTraderBot.vbs` in the Startup folder)
- `.venv/` — Python virtual environment with freqtrade installed

## Websites

- **Dashboard (read-only):** http://127.0.0.1:3000 — balance, profit, trades, daily chart
- **freqUI (full control panel):** http://127.0.0.1:8080 — login `trader` / see `config.json`

While the bot runs on this PC both are local-only. Deploying to a server
(`DEPLOY.md`) makes the dashboard public at `http://SERVER_IP` while keeping
the control panel private.

## Common commands

Run these from this folder. Use the venv's freqtrade:

```powershell
$ft = ".\.venv\Scripts\freqtrade.exe"

# Download/refresh historical data
& $ft download-data --config config.json --timeframes 1h 4h --days 730

# Backtest a strategy
& $ft backtesting --config config.json --strategy TrendFollowStrategy --timerange 20240601-

# Compare both strategies
& $ft backtesting --config config.json --strategy-list TrendFollowStrategy MeanReversionStrategy --timerange 20240601-

# Start paper trading (live prices, fake money) + web UI at http://127.0.0.1:8080
& $ft trade --config config.json --strategy TrendFollowStrategy
```

Web UI login is set in `config.json` under `api_server` (user `trader`).

## Safety rules (do not break these)

- `dry_run` stays `true` until strategies have proven themselves for weeks.
- If/when going live: API keys must be **trade-only** (withdrawals disabled),
  and start with a small stake.
- Never commit API keys to git or share them.
