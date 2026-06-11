"""Market structure analysis on the downloaded candle data.

Answers: what regimes did the market go through, how volatile is each pair,
how correlated are they, and which strategy styles each regime favors.
Run after `freqtrade download-data`. Prints a plain-text report.
"""

import os

import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "user_data", "data", "binance")
PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "BNB_USDT", "XRP_USDT", "ADA_USDT", "LINK_USDT", "AVAX_USDT"]


def load_daily(pair: str) -> pd.DataFrame:
    df = pd.read_feather(os.path.join(DATA_DIR, f"{pair}-1d.feather"))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def main() -> None:
    btc = load_daily("BTC_USDT")
    print(f"BTC data: {btc.index[0]:%Y-%m-%d} -> {btc.index[-1]:%Y-%m-%d} ({len(btc)} days)\n")

    # --- Quarterly regime table for BTC ---
    print("=== BTC quarterly regimes ===")
    print(f"{'quarter':<8} {'return%':>8} {'maxDD%':>7} {'ann.vol%':>8}  regime")
    q = btc["close"].resample("QE")
    for period, closes in q:
        if len(closes) < 30:
            continue
        ret = closes.iloc[-1] / closes.iloc[0] - 1
        dd = (closes / closes.cummax() - 1).min()
        vol = closes.pct_change().std() * np.sqrt(365)
        if ret > 0.15:
            regime = "BULL"
        elif ret < -0.15:
            regime = "BEAR"
        else:
            regime = "chop"
        print(f"{period.year}-Q{period.quarter}  {100*ret:>7.1f} {100*dd:>7.1f} {100*vol:>8.1f}  {regime}")

    # --- Trendiness: how often is BTC above its 200d MA, and does it persist? ---
    ma200 = btc["close"].rolling(200).mean()
    above = (btc["close"] > ma200).dropna()
    flips = (above != above.shift()).sum()
    print(f"\nBTC above 200d MA: {100 * above.mean():.0f}% of days, regime flips: {flips} "
          f"(avg regime length {len(above) / max(flips, 1):.0f} days)")

    # --- Per-pair stats over full period ---
    print("\n=== Per-pair stats (full period, daily) ===")
    print(f"{'pair':<10} {'total%':>8} {'ann.vol%':>8} {'maxDD%':>7} {'corr/BTC':>8}")
    btc_ret = btc["close"].pct_change()
    for pair in PAIRS:
        try:
            df = load_daily(pair)
        except Exception:
            continue
        ret = df["close"].iloc[-1] / df["close"].iloc[0] - 1
        vol = df["close"].pct_change().std() * np.sqrt(365)
        dd = (df["close"] / df["close"].cummax() - 1).min()
        corr = df["close"].pct_change().corr(btc_ret)
        print(f"{pair:<10} {100*ret:>8.1f} {100*vol:>8.1f} {100*dd:>7.1f} {corr:>8.2f}")

    # --- Autocorrelation: do daily returns trend or mean-revert? ---
    print("\n=== Return autocorrelation (BTC) ===")
    for lag in (1, 2, 5, 10):
        ac = btc_ret.autocorr(lag)
        print(f"lag {lag:>2}d: {ac:+.3f}")
    r4h = pd.read_feather(os.path.join(DATA_DIR, "BTC_USDT-4h.feather"))["close"].pct_change()
    print(f"lag 1 (4h candles): {r4h.autocorr(1):+.3f}")

    # --- Suggested backtest windows (calendar-based, printed for reuse) ---
    print("\n=== Suggested regime windows for backtesting ===")
    start = btc.index[0] + pd.Timedelta(days=35)  # leave startup-candle room
    print(f"full     : {start:%Y%m%d}-")
    print("bear-2022: 20220801-20230101  (if data reaches)")
    print("bull     : 20230901-20250101")
    print("recent   : 20250101-")


if __name__ == "__main__":
    main()
