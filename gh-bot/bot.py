"""Self-contained paper-trading engine, designed to run on GitHub Actions.

Each run (hourly via cron) it:
  1. fetches 4h candles for each pair from Kraken's public API (no keys),
  2. applies the TrendFollow rules (EMA 21/55 cross, 200-EMA trend filter,
     RSI < 70) to open/close simulated positions,
  3. persists the simulated wallet to gh-bot/state.json,
  4. writes docs/data.json for the GitHub Pages dashboard.

All trades are simulated. No API keys, no real money, no withdrawals possible.
Stops/ROI are evaluated at run granularity (hourly), which is honest enough
for a 4h strategy but slightly optimistic vs. real intra-candle execution.
"""

import json
import os
from datetime import datetime, timezone

import ccxt
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(ROOT, "state.json")
SITE_DATA = os.path.join(ROOT, "..", "docs", "data.json")

EXCHANGE_ID = "kraken"  # public data works worldwide, incl. GitHub's US runners
PAIRS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD", "LINK/USD", "AVAX/USD"]
TIMEFRAME = "4h"
MAX_OPEN_TRADES = 3
START_BALANCE = 10_000.0
FEE = 0.0026  # Kraken taker fee, charged on entry and exit

STOPLOSS = -0.06
# (trade age in minutes, profit target) — freqtrade-style ROI ladder
ROI_LADDER = [(1440, 0.02), (720, 0.03), (360, 0.05), (0, 0.08)]
TRAIL_TRIGGER = 0.04  # start trailing once profit peaked above 4%
TRAIL_DISTANCE = 0.02  # then exit if price falls 2% below the peak


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    return {
        "cash": START_BALANCE,
        "open_trades": [],
        "closed_trades": [],
        "equity_history": [],
        "created_at": now_utc(),
    }


def fetch_candles(exchange, pair: str) -> tuple[pd.DataFrame, float]:
    """Return (closed candles with indicators, current price)."""
    raw = exchange.fetch_ohlcv(pair, TIMEFRAME, limit=300)
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    price_now = float(df["close"].iloc[-1])
    closed = df.iloc[:-1].copy()  # last candle is still forming
    closed["ema_fast"] = ema(closed["close"], 21)
    closed["ema_slow"] = ema(closed["close"], 55)
    closed["ema_trend"] = ema(closed["close"], 200)
    closed["rsi"] = rsi(closed["close"])
    return closed, price_now


def entry_signal(closed: pd.DataFrame) -> bool:
    cur, prev = closed.iloc[-1], closed.iloc[-2]
    crossed_up = prev["ema_fast"] <= prev["ema_slow"] and cur["ema_fast"] > cur["ema_slow"]
    return bool(
        crossed_up
        and cur["close"] > cur["ema_trend"]
        and cur["rsi"] < 70
        and cur["volume"] > 0
    )


def exit_signal(closed: pd.DataFrame) -> bool:
    cur, prev = closed.iloc[-1], closed.iloc[-2]
    return bool(prev["ema_fast"] >= prev["ema_slow"] and cur["ema_fast"] < cur["ema_slow"])


def roi_target(age_minutes: float) -> float:
    return next(target for minutes, target in ROI_LADDER if age_minutes >= minutes)


def check_exit(trade: dict, closed: pd.DataFrame, price_now: float) -> str | None:
    profit = price_now / trade["open_price"] - 1
    trade["peak_price"] = max(trade.get("peak_price", trade["open_price"]), price_now)
    peak_profit = trade["peak_price"] / trade["open_price"] - 1

    if profit <= STOPLOSS:
        return "stop_loss"
    if peak_profit >= TRAIL_TRIGGER and price_now <= trade["peak_price"] * (1 - TRAIL_DISTANCE):
        return "trailing_stop"
    age = (
        datetime.now(timezone.utc)
        - datetime.fromisoformat(trade["open_time"]).replace(tzinfo=timezone.utc)
    ).total_seconds() / 60
    if profit >= roi_target(age):
        return "roi"
    if exit_signal(closed):
        return "exit_signal"
    return None


def close_trade(state: dict, trade: dict, price: float, reason: str) -> None:
    proceeds = trade["qty"] * price * (1 - FEE)
    state["cash"] += proceeds
    profit_abs = proceeds - trade["stake"]
    state["closed_trades"].append(
        {
            "pair": trade["pair"],
            "open_price": trade["open_price"],
            "close_price": price,
            "stake": trade["stake"],
            "profit_abs": round(profit_abs, 2),
            "profit_pct": round(100 * profit_abs / trade["stake"], 2),
            "open_time": trade["open_time"],
            "close_time": now_utc(),
            "exit_reason": reason,
        }
    )
    state["open_trades"] = [t for t in state["open_trades"] if t["pair"] != trade["pair"]]
    print(f"CLOSE {trade['pair']} @ {price:.4f} ({reason}) profit {profit_abs:+.2f} USD")


def open_trade(state: dict, pair: str, price: float) -> None:
    slots_left = MAX_OPEN_TRADES - len(state["open_trades"])
    stake = min(state["cash"] / slots_left, state["cash"])
    if stake < 10:  # don't open dust positions
        return
    qty = stake * (1 - FEE) / price
    state["cash"] -= stake
    state["open_trades"].append(
        {
            "pair": pair,
            "open_price": price,
            "qty": qty,
            "stake": stake,
            "peak_price": price,
            "open_time": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", ""),
        }
    )
    print(f"OPEN  {pair} @ {price:.4f} stake {stake:.2f} USD")


def main() -> None:
    state = load_state()
    exchange = getattr(ccxt, EXCHANGE_ID)({"enableRateLimit": True})

    prices: dict[str, float] = {}
    for pair in PAIRS:
        try:
            closed, price_now = fetch_candles(exchange, pair)
        except Exception as exc:  # one bad pair shouldn't kill the whole run
            print(f"WARN  {pair}: data fetch failed: {exc}")
            continue
        prices[pair] = price_now

        open_trade_for_pair = next(
            (t for t in state["open_trades"] if t["pair"] == pair), None
        )
        if open_trade_for_pair:
            reason = check_exit(open_trade_for_pair, closed, price_now)
            if reason:
                close_trade(state, open_trade_for_pair, price_now, reason)
        elif len(state["open_trades"]) < MAX_OPEN_TRADES and entry_signal(closed):
            open_trade(state, pair, price_now)

    equity = state["cash"] + sum(
        t["qty"] * prices.get(t["pair"], t["open_price"]) for t in state["open_trades"]
    )
    state["equity_history"].append({"t": now_utc(), "equity": round(equity, 2)})
    state["equity_history"] = state["equity_history"][-5000:]

    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)

    closed_trades = state["closed_trades"]
    wins = sum(1 for t in closed_trades if t["profit_abs"] > 0)
    losses = len(closed_trades) - wins
    site = {
        "generated_at": now_utc(),
        "exchange": EXCHANGE_ID,
        "timeframe": TIMEFRAME,
        "strategy": "TrendFollow (EMA 21/55 cross, 200-EMA filter, RSI < 70)",
        "dry_run": True,
        "start_balance": START_BALANCE,
        "cash": round(state["cash"], 2),
        "equity": round(equity, 2),
        "stats": {
            "closed_profit_abs": round(sum(t["profit_abs"] for t in closed_trades), 2),
            "trade_count": len(closed_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": round(100 * wins / len(closed_trades), 1) if closed_trades else None,
        },
        "open_trades": [
            {
                **t,
                "current_price": prices.get(t["pair"]),
                "profit_pct": round(100 * (prices.get(t["pair"], t["open_price"]) / t["open_price"] - 1), 2),
                "profit_abs": round(t["qty"] * prices.get(t["pair"], t["open_price"]) - t["stake"], 2),
            }
            for t in state["open_trades"]
        ],
        "closed_trades": closed_trades[-20:][::-1],
        "equity_history": state["equity_history"],
    }
    os.makedirs(os.path.dirname(SITE_DATA), exist_ok=True)
    with open(SITE_DATA, "w", encoding="utf-8") as fh:
        json.dump(site, fh, indent=1)

    print(
        f"DONE  {now_utc()} | equity {equity:.2f} USD | cash {state['cash']:.2f} | "
        f"open {len(state['open_trades'])} | closed {len(closed_trades)}"
    )


if __name__ == "__main__":
    main()
