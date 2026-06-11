# Regime-following: systematized buy-and-hold with crash protection.
#
# Lesson from the 24-backtest matrix (research/results.md): fast strategies
# beat the market in bears but give up nearly all bull-market upside because
# ROI ladders and tight stops cut winners. Meanwhile the market analysis
# shows crypto regimes persist for ~6 weeks on average.
#
# So: hold a pair while it trades above its 200-day EMA (with a hysteresis
# band to avoid whipsaw), exit to cash when the regime breaks. No profit
# caps — the whole point is to capture the bull runs and skip the crashes.
# Expect very few trades and long hold times.

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class RegimeHoldStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1d"
    can_short = False

    minimal_roi = {"0": 100}  # disabled — never exit just because of profit

    stoploss = -0.15  # disaster brake only; the regime exit is the real stop

    trailing_stop = False

    startup_candle_count = 210

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 2% band above the EMA: price must clear it decisively
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["ema200"] * 1.02)
                & (dataframe["close"].shift(1) <= dataframe["ema200"].shift(1) * 1.02)
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 3% band below the EMA: regime is broken, go to cash
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["ema200"] * 0.97)
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        return dataframe
