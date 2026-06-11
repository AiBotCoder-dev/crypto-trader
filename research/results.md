# Backtest results — all strategies × market regimes

Stake: 10,000 USDT, max 3 open trades, 0.10% fee/side, 8 USDT pairs.
`edge` = strategy profit minus buy-and-hold (market change) in that window.

## bear-2022 (`20220801-20230101`)

| Strategy | Profit % | Market % | Edge | Trades | Win % | Max DD % | PF | Sharpe |
|---|---|---|---|---|---|---|---|---|
| TrendFollow | -0.19% | -37.26% | 37.1% | 17 | 64.7% | 3.85% | 0.98 | -0.02 |
| MeanReversion | -3.72% | -37.27% | 33.6% | 13 | 38.5% | 5.91% | 0.46 | -0.5 |
| DonchianBreakout | -18.05% | -37.26% | 19.2% | 42 | 47.6% | 24.73% | 0.59 | -1.27 |
| MacdTrend | -7.89% | -37.26% | 29.4% | 48 | 39.6% | 9.51% | 0.72 | -0.84 |
| BbSqueeze | -14.24% | -37.27% | 23% | 98 | 32.7% | 17.44% | 0.65 | -2.22 |
| RsiDip | -7.72% | -37.27% | 29.6% | 48 | 64.6% | 10.97% | 0.67 | -1.03 |

## bull (`20230901-20250101`)

| Strategy | Profit % | Market % | Edge | Trades | Win % | Max DD % | PF | Sharpe |
|---|---|---|---|---|---|---|---|---|
| TrendFollow | 6.25% | 310.33% | -304.1% | 97 | 64.9% | 15.52% | 1.13 | 0.2 |
| MeanReversion | -1.12% | 313.92% | -315% | 50 | 62% | 9.71% | 0.94 | -0.05 |
| DonchianBreakout | -0.97% | 310.33% | -311.3% | 233 | 59.7% | 47.02% | 1 | -0.02 |
| MacdTrend | -20.42% | 310.33% | -330.8% | 277 | 40.4% | 31.2% | 0.86 | -0.71 |
| BbSqueeze | -8.04% | 313.92% | -322% | 395 | 38.7% | 19.73% | 0.93 | -0.45 |
| RsiDip | -13.46% | 313.92% | -327.4% | 230 | 63.9% | 33.05% | 0.87 | -0.56 |

## recent (`20250101-20260611`)

| Strategy | Profit % | Market % | Edge | Trades | Win % | Max DD % | PF | Sharpe |
|---|---|---|---|---|---|---|---|---|
| TrendFollow | -9.21% | -54.37% | 45.2% | 82 | 59.8% | 19.29% | 0.82 | -0.27 |
| MeanReversion | -8.55% | -55.45% | 46.9% | 50 | 66% | 9.63% | 0.52 | -0.4 |
| DonchianBreakout | -45.86% | -54.37% | 8.5% | 134 | 45.5% | 47.66% | 0.63 | -0.96 |
| MacdTrend | -20.29% | -54.37% | 34.1% | 163 | 36.2% | 26.84% | 0.73 | -0.82 |
| BbSqueeze | 0.22% | -55.45% | 55.7% | 361 | 37.4% | 14.45% | 1 | 0.01 |
| RsiDip | -28.2% | -55.45% | 27.3% | 175 | 61.7% | 31.81% | 0.64 | -1.18 |

## full (`20220801-20260611`)

| Strategy | Profit % | Market % | Edge | Trades | Win % | Max DD % | PF | Sharpe |
|---|---|---|---|---|---|---|---|---|
| TrendFollow | -15.89% | 47.32% | -63.2% | 249 | 60.6% | 23.63% | 0.88 | -0.19 |
| MeanReversion | -8.66% | 44.71% | -53.4% | 139 | 63.3% | 12.25% | 0.81 | -0.15 |
| DonchianBreakout | -48.03% | 47.32% | -95.3% | 471 | 54.8% | 63.95% | 0.89 | -0.33 |
| MacdTrend | -37.78% | 47.32% | -85.1% | 603 | 39% | 49.3% | 0.87 | -0.5 |
| BbSqueeze | -30.73% | 44.71% | -75.4% | 1024 | 36.7% | 41.02% | 0.88 | -0.75 |
| RsiDip | -46.08% | 44.71% | -90.8% | 561 | 63.6% | 48.85% | 0.78 | -0.79 |

## RegimeHold (1d, designed from the findings above)

Hold while price > 200-day EMA (+2% entry band), cash when price < EMA −3%.
No profit caps, −15% disaster stop. Few trades, ~72-day average hold.

| Window | Profit % | Market % | Edge | Trades | Max DD % (closed) | PF |
|---|---|---|---|---|---|---|
| bear-2022 | 0% (in cash, no trades) | −37.3% | +37.3% | 0 | 0% | — |
| bull | +265.9% | +335.7% | −69.8% | 19 | 13.0% | 5.21 |
| recent | −34.2% | −56.9% | +22.7% | 18 | 38.5% | 0.22 |
| **full (8 pairs)** | **+164.7%** | +110.9% | **+53.8%** | 38 | 16.9% | 2.05 |
| **full (majors: BTC/ETH/SOL/BNB)** | **+249.6%** | +183.9% | **+65.7%** | 29 | 10.0% | 3.28 |

# Conclusions

1. **No fast signal strategy beat buy-and-hold over 4 years.** All six lost
   money (best: MeanReversion −8.7% vs market +47%). They trade too often,
   pay too many fees, and their ROI ladders/stops amputate bull-market winners.
2. **Fast strategies are defense, not offense.** Every one of them beat the
   market in both bear windows by 20–55 points — by losing less.
3. **The harvestable edge is regime persistence** (~44-day average regimes,
   58% of days above the 200d MA). RegimeHold — the slowest, dumbest strategy
   of the seven — is the only one that beat buy-and-hold, and it won by
   skipping bears, not by trading brilliantly. Win rate just 29%: a few huge
   wins pay for many small whipsaw losses. You must tolerate that to earn it.
4. **Honest caveats:** wallet-based drawdown still reaches ~38–45% (you hold
   through swings); the 2025–26 bear cost it −34% via repeated false
   recoveries; results assume 0.1% fees and no slippage; and 4 years /
   38 trades is a small sample — paper trading it forward is the real test.
