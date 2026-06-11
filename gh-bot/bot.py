"""Self-contained paper-trading engine, designed to run on GitHub Actions.

Strategy: RegimeHold — the only strategy that beat buy-and-hold in our
4-year backtest matrix (research/results.md). Hold a coin while its last
closed daily candle is above the 200-day EMA +2% band; exit to cash when it
closes below the EMA −3% band, or on a −15% disaster stop. No profit caps —
the edge comes from riding bull regimes fully and skipping crashes.

Position sizing: no position-count cap. Every pair gets an equal-weight
slice of total equity (bounded by available cash), so the bot can be fully
invested across the whole universe when everything is in a bull regime.
This maximizes signal samples for strategy evaluation — fine for paper
trading; a live configuration would reintroduce concentration limits.

Each hourly run also publishes per-pair signal levels (exact entry/exit
trigger prices and distances) to docs/data.json for the dashboard.

All trades are simulated. No API keys, no real money.
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
PAIRS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD",
    "LINK/USD", "AVAX/USD", "DOT/USD", "DOGE/USD", "LTC/USD",
    "BCH/USD", "ATOM/USD", "UNI/USD", "AAVE/USD", "FIL/USD",
]
TIMEFRAME = "1d"
START_BALANCE = 10_000.0
FEE = 0.0026  # Kraken taker fee, charged on entry and exit

EMA_PERIOD = 200
ENTRY_BAND = 1.02   # last daily close must clear EMA by +2% to enter
EXIT_BAND = 0.97    # close below EMA -3% means the regime broke
STOPLOSS = -0.15    # disaster brake, checked against live price hourly


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as fh:
            state = json.load(fh)
        state.setdefault("cash", START_BALANCE)
        state.setdefault("open_trades", [])
        state.setdefault("closed_trades", [])
        state.setdefault("equity_history", [])
        return state
    return {
        "cash": START_BALANCE,
        "open_trades": [],
        "closed_trades": [],
        "equity_history": [],
        "created_at": now_utc(),
    }


def fetch_pair(exchange, pair: str) -> dict:
    """Return regime info for one pair from daily candles."""
    raw = exchange.fetch_ohlcv(pair, TIMEFRAME, limit=EMA_PERIOD + 100)
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    price_now = float(df["close"].iloc[-1])
    closed = df.iloc[:-1]  # last candle is still forming
    if len(closed) < EMA_PERIOD:
        raise ValueError(f"only {len(closed)} closed daily candles")
    ema = float(closed["close"].ewm(span=EMA_PERIOD, adjust=False).mean().iloc[-1])
    last_close = float(closed["close"].iloc[-1])
    return {
        "price": price_now,
        "ema200": ema,
        "last_daily_close": last_close,
        "entry_level": ema * ENTRY_BAND,
        "exit_level": ema * EXIT_BAND,
        "regime": "bull" if last_close > ema * ENTRY_BAND
        else "bear" if last_close < ema * EXIT_BAND
        else "neutral",
    }


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


def open_trade(state: dict, pair: str, price: float, equity: float) -> None:
    stake = min(equity / len(PAIRS), state["cash"])
    if stake < 10:  # not enough cash for a meaningful position
        return
    qty = stake * (1 - FEE) / price
    state["cash"] -= stake
    state["open_trades"].append(
        {
            "pair": pair,
            "open_price": price,
            "qty": qty,
            "stake": stake,
            "open_time": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", ""),
        }
    )
    print(f"OPEN  {pair} @ {price:.4f} stake {stake:.2f} USD")


def main() -> None:
    state = load_state()
    exchange = getattr(ccxt, EXCHANGE_ID)({"enableRateLimit": True})

    infos: dict[str, dict] = {}
    for pair in PAIRS:
        try:
            infos[pair] = fetch_pair(exchange, pair)
        except Exception as exc:  # one bad pair shouldn't kill the whole run
            print(f"WARN  {pair}: data fetch failed: {exc}")

    def price_of(trade):
        return infos[trade["pair"]]["price"] if trade["pair"] in infos else trade["open_price"]

    equity = state["cash"] + sum(t["qty"] * price_of(t) for t in state["open_trades"])

    # Exits first (frees cash for same-run entries)
    for trade in list(state["open_trades"]):
        info = infos.get(trade["pair"])
        if not info:
            continue
        profit = info["price"] / trade["open_price"] - 1
        if profit <= STOPLOSS:
            close_trade(state, trade, info["price"], "stop_loss")
        elif info["last_daily_close"] < info["exit_level"]:
            close_trade(state, trade, info["price"], "regime_exit")

    # Entries: any pair in a bull regime that we don't already hold
    held = {t["pair"] for t in state["open_trades"]}
    for pair, info in infos.items():
        if pair not in held and info["regime"] == "bull":
            open_trade(state, pair, info["price"], equity)

    equity = state["cash"] + sum(t["qty"] * price_of(t) for t in state["open_trades"])
    state["equity_history"].append({"t": now_utc(), "equity": round(equity, 2)})
    state["equity_history"] = state["equity_history"][-5000:]

    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)

    closed_trades = state["closed_trades"]
    wins = sum(1 for t in closed_trades if t["profit_abs"] > 0)
    losses = len(closed_trades) - wins
    held = {t["pair"]: t for t in state["open_trades"]}
    site = {
        "generated_at": now_utc(),
        "exchange": EXCHANGE_ID,
        "timeframe": TIMEFRAME,
        "strategy": "RegimeHold (200-day EMA, +2%/-3% bands, no profit caps)",
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
        "signals": [
            {
                "pair": pair,
                "price": round(info["price"], 6),
                "ema200": round(info["ema200"], 6),
                "regime": info["regime"],
                "holding": pair in held,
                "entry_level": round(info["entry_level"], 6),
                "exit_level": round(info["exit_level"], 6),
                "stop_level": round(held[pair]["open_price"] * (1 + STOPLOSS), 6) if pair in held else None,
                "distance_pct": round(
                    100 * (info["exit_level"] / info["price"] - 1)
                    if pair in held
                    else 100 * (info["entry_level"] / info["price"] - 1),
                    2,
                ),
            }
            for pair, info in sorted(infos.items())
        ],
        "open_trades": [
            {
                **t,
                "current_price": infos[t["pair"]]["price"] if t["pair"] in infos else None,
                "profit_pct": round(100 * (price_of(t) / t["open_price"] - 1), 2),
                "profit_abs": round(t["qty"] * price_of(t) - t["stake"], 2),
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
        f"open {len(state['open_trades'])}/{len(PAIRS)} | closed {len(closed_trades)}"
    )


if __name__ == "__main__":
    main()
