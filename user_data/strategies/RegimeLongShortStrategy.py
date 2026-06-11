# Long/short regime following on perpetual futures, 1x leverage.
#
# Extends RegimeHoldStrategy's finding (the only strategy that beat
# buy-and-hold over 4y) to the short side: long while price is decisively
# above the 200-day EMA, short while decisively below it, flat in the
# hysteresis band between. Funding fees are modeled by freqtrade's futures
# backtesting. Deliberately unleveraged: the edge being tested is the regime
# signal, not leverage.

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class RegimeLongShortStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1d"
    can_short = True

    minimal_roi = {"0": 100}  # disabled — regime exits do the work

    stoploss = -0.15

    trailing_stop = False

    startup_candle_count = 210

    def leverage(self, pair: str, current_time, current_rate,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag, side: str, **kwargs) -> float:
        return 1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["ema200"] * 1.02)
                & (dataframe["close"].shift(1) <= dataframe["ema200"].shift(1) * 1.02)
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        # Shorts additionally require the EMA itself to be falling — price
        # merely dipping below a rising EMA is chop, not a downtrend.
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["ema200"] * 0.98)
                & (dataframe["close"].shift(1) >= dataframe["ema200"].shift(1) * 0.98)
                & (dataframe["ema200"] < dataframe["ema200"].shift(10))
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["ema200"] * 0.97)
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["ema200"] * 1.03)
                & (dataframe["volume"] > 0)
            ),
            "exit_short",
        ] = 1
        return dataframe
