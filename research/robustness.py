"""Robustness testing for RegimeHold: parameter sweep + walk-forward.

Questions answered:
1. Does the edge survive across a grid of EMA lengths and entry/exit bands,
   or does it only exist at the exact parameters we happened to pick?
2. Walk-forward: pick the best config on 2022-08..2024-12 (in-sample), then
   evaluate it on 2025-01..2026-06 (out-of-sample, never seen during tuning).

Simulator notes: simplified daily-bar engine (signals on a day's close,
executed at next day's open; -15% stop checked against the day's low;
0.1% fee per side; equal-weight portfolio = average of per-pair equity
curves). It approximates but does not exactly reproduce freqtrade's engine —
use it for *relative* comparisons across configs, not absolute numbers.
"""

import os

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "user_data", "data", "binance")
PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT", "ADA_USDT", "LINK_USDT", "AVAX_USDT"]
FEE = 0.001
STOP = -0.15

EMA_GRID = [100, 150, 200, 250, 300]
ENTRY_GRID = [0.00, 0.01, 0.02, 0.03, 0.05]
EXIT_GRID = [-0.01, -0.03, -0.05]

IS_END = "2024-12-31"   # in-sample boundary for walk-forward
START = "2022-08-01"


def load(pair: str) -> pd.DataFrame:
    df = pd.read_feather(os.path.join(DATA_DIR, f"{pair}-1d.feather"))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[["open", "high", "low", "close"]]


def sim_pair(df: pd.DataFrame, ema_n: int, entry_b: float, exit_b: float) -> pd.Series:
    ema = df["close"].ewm(span=ema_n, adjust=False).mean()
    enter_sig = (df["close"] > ema * (1 + entry_b)).values
    exit_sig = (df["close"] < ema * (1 + exit_b)).values
    o, l, c = df["open"].values, df["low"].values, df["close"].values

    cash, qty, entry_px = 1.0, 0.0, 0.0
    equity = np.empty(len(df))
    for i in range(len(df)):
        if i > ema_n:  # EMA warm-up
            if qty == 0 and enter_sig[i - 1]:
                qty = cash * (1 - FEE) / o[i]
                cash, entry_px = 0.0, o[i]
            elif qty > 0 and exit_sig[i - 1]:
                cash, qty = qty * o[i] * (1 - FEE), 0.0
        if qty > 0 and l[i] <= entry_px * (1 + STOP):
            cash, qty = qty * entry_px * (1 + STOP) * (1 - FEE), 0.0
        equity[i] = cash + qty * c[i]
    return pd.Series(equity, index=df.index)


def portfolio_curve(dfs: dict, ema_n: int, entry_b: float, exit_b: float,
                    start: str, end: str | None) -> pd.Series:
    curves = []
    for pair, df in dfs.items():
        win = df.loc[:end] if end else df
        eq = sim_pair(win, ema_n, entry_b, exit_b).loc[start:]
        curves.append(eq / eq.iloc[0])
    aligned = pd.concat(curves, axis=1).ffill()
    return aligned.mean(axis=1)


def hold_return(dfs: dict, start: str, end: str | None) -> float:
    rets = []
    for df in dfs.values():
        win = df.loc[start:end] if end else df.loc[start:]
        rets.append(win["close"].iloc[-1] / win["close"].iloc[0] - 1)
    return float(np.mean(rets))


def main() -> None:
    dfs = {p: load(p) for p in PAIRS}

    market_full = hold_return(dfs, START, None)
    print(f"Equal-weight buy & hold, full period: {100 * market_full:+.1f}%\n")

    print(f"{'ema':>4} {'entry':>6} {'exit':>6} | {'full %':>8} {'IS %':>8} {'OOS %':>8}")
    rows = []
    for ema_n in EMA_GRID:
        for entry_b in ENTRY_GRID:
            for exit_b in EXIT_GRID:
                full = portfolio_curve(dfs, ema_n, entry_b, exit_b, START, None)
                full_ret = full.iloc[-1] / full.iloc[0] - 1
                is_ret = full.loc[:IS_END].iloc[-1] / full.iloc[0] - 1
                oos_ret = full.iloc[-1] / full.loc[:IS_END].iloc[-1] - 1
                rows.append({
                    "ema": ema_n, "entry": entry_b, "exit": exit_b,
                    "full": full_ret, "is": is_ret, "oos": oos_ret,
                })
                print(f"{ema_n:>4} {entry_b:>6.2f} {exit_b:>6.2f} | "
                      f"{100*full_ret:>7.1f}% {100*is_ret:>7.1f}% {100*oos_ret:>7.1f}%")

    res = pd.DataFrame(rows)
    beat = (res["full"] > market_full).mean()
    print(f"\nConfigs tested: {len(res)}")
    print(f"Share beating buy & hold over full period: {100 * beat:.0f}%")
    print(f"Full-period return: median {100 * res['full'].median():+.1f}%, "
          f"min {100 * res['full'].min():+.1f}%, max {100 * res['full'].max():+.1f}%")

    base = res[(res.ema == 200) & (res.entry == 0.02) & (res.exit == -0.03)].iloc[0]
    print(f"\nOur deployed config (ema200, +2%/-3%): full {100*base['full']:+.1f}%, "
          f"IS {100*base['is']:+.1f}%, OOS {100*base['oos']:+.1f}%")

    # Walk-forward: pick best in-sample config, evaluate out-of-sample
    best_is = res.sort_values("is", ascending=False).iloc[0]
    market_oos = hold_return(dfs, IS_END, None)
    print(f"\nWalk-forward:")
    print(f"  best in-sample config: ema{int(best_is['ema'])}, "
          f"entry +{100*best_is['entry']:.0f}%, exit {100*best_is['exit']:.0f}% "
          f"(IS {100*best_is['is']:+.1f}%)")
    print(f"  its out-of-sample return: {100*best_is['oos']:+.1f}%")
    print(f"  buy & hold out-of-sample:  {100*market_oos:+.1f}%")
    print(f"  median OOS across all configs: {100*res['oos'].median():+.1f}%")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robustness_grid.csv")
    res.to_csv(out, index=False)
    print(f"\nGrid saved to {out}")


if __name__ == "__main__":
    main()
