"""Backtest every strategy across every market-regime window and tabulate.

Runs freqtrade backtesting via subprocess, scrapes the summary metrics from
stdout, and writes a markdown comparison to research/results.md.
"""

import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FREQTRADE = os.path.join(ROOT, ".venv", "Scripts", "freqtrade.exe")
RESULTS_MD = os.path.join(ROOT, "research", "results.md")

STRATEGIES = [
    "TrendFollowStrategy",
    "MeanReversionStrategy",
    "DonchianBreakoutStrategy",
    "MacdTrendStrategy",
    "BbSqueezeStrategy",
    "RsiDipStrategy",
]

WINDOWS = {
    "bear-2022": "20220801-20230101",
    "bull": "20230901-20250101",
    "recent": "20250101-20260611",
    "full": "20220801-20260611",
}

METRIC_PATTERNS = {
    "profit_pct": r"\|\s*Total profit %\s*\|\s*(-?[\d.]+)%",
    "market_pct": r"\|\s*Market change\s*\|\s*(-?[\d.]+)%",
    "trades": r"\|\s*Total/Daily Avg Trades\s*\|\s*(\d+)",
    "win_rate": r"\|\s*Days win/draw/lose.*",  # placeholder, win% taken from summary row
    "drawdown_pct": r"\|\s*Max % of account underwater\s*\|\s*([\d.]+)%",
    "profit_factor": r"\|\s*Profit factor\s*\|\s*([\d.]+)",
    "sharpe": r"\|\s*Sharpe \(closed trades\)\s*\|\s*(-?[\d.]+)",
}


def run_backtest(strategy: str, timerange: str) -> dict:
    cmd = [
        FREQTRADE, "backtesting",
        "--config", os.path.join(ROOT, "config.json"),
        "--userdir", os.path.join(ROOT, "user_data"),
        "--strategy", strategy,
        "--timerange", timerange,
        "--export", "none",
    ]
    out = subprocess.run(
        cmd, capture_output=True, text=True, cwd=ROOT, timeout=600
    ).stdout

    row: dict = {}
    for key, pattern in METRIC_PATTERNS.items():
        if key == "win_rate":
            continue
        m = re.search(pattern, out)
        row[key] = float(m.group(1)) if m else None

    # Win% from the final STRATEGY SUMMARY row:  Win  Draw  Loss  Win%
    m = re.search(r"\|\s*" + strategy + r"\s*\|.*?(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s*\|", out)
    row["win_pct"] = float(m.group(4)) if m else None
    if row.get("profit_pct") is None:
        # No trades at all in this window
        m2 = re.search(r"No trades made", out)
        row["note"] = "no trades" if m2 else "parse error"
    return row


def fmt(v, suffix=""):
    return "—" if v is None else f"{v:g}{suffix}"


def main() -> None:
    lines = [
        "# Backtest results — all strategies × market regimes",
        "",
        "Stake: 10,000 USDT, max 3 open trades, 0.10% fee/side, 8 USDT pairs.",
        "`edge` = strategy profit minus buy-and-hold (market change) in that window.",
        "",
    ]
    for window, timerange in WINDOWS.items():
        print(f"\n=== {window} ({timerange}) ===")
        lines += [f"## {window} (`{timerange}`)", ""]
        lines.append("| Strategy | Profit % | Market % | Edge | Trades | Win % | Max DD % | PF | Sharpe |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for strategy in STRATEGIES:
            r = run_backtest(strategy, timerange)
            edge = (
                None
                if r.get("profit_pct") is None or r.get("market_pct") is None
                else round(r["profit_pct"] - r["market_pct"], 1)
            )
            line = (
                f"| {strategy.replace('Strategy', '')} | {fmt(r.get('profit_pct'), '%')} | "
                f"{fmt(r.get('market_pct'), '%')} | {fmt(edge, '%')} | {fmt(r.get('trades'))} | "
                f"{fmt(r.get('win_pct'), '%')} | {fmt(r.get('drawdown_pct'), '%')} | "
                f"{fmt(r.get('profit_factor'))} | {fmt(r.get('sharpe'))} |"
            )
            lines.append(line)
            print(line)
        lines.append("")

    with open(RESULTS_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"\nWritten to {RESULTS_MD}")


if __name__ == "__main__":
    main()
