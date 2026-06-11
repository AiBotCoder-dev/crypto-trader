# Donchian channel breakout (classic turtle-style trend following).
#
# Idea: buy when price breaks above its 55-candle high while the trend is
# strong (ADX filter); ride it and exit when price breaks below the
# 20-candle low. No profit target ladder — let winners run, the exit channel
# and trailing stop do the work. Suited to crypto's multi-week trend regimes.

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class DonchianBreakoutStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "4h"
    can_short = False

    minimal_roi = {"0": 0.30}  # effectively "let it run"; exits do the work

    stoploss = -0.08

    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.06
    trailing_only_offset_is_reached = True

    startup_candle_count = 60

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["don_high"] = dataframe["high"].rolling(55).max().shift(1)
        dataframe["don_low"] = dataframe["low"].rolling(20).min().shift(1)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["don_high"])
                & (dataframe["adx"] > 22)
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["don_low"])
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        return dataframe
