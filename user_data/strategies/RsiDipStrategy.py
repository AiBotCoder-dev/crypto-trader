# RSI dip-buying inside a confirmed uptrend (disciplined mean reversion).
#
# Idea: in an uptrend (EMA50 above EMA200, price above EMA200), short-term
# panic dips (RSI < 35) tend to bounce. Buy the dip, sell the recovery
# (RSI > 60) or take small profits via the ROI ladder. The tight stop keeps
# the inevitable "dip keeps dipping" cases small.

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class RsiDipStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False

    minimal_roi = {
        "0": 0.04,
        "360": 0.025,
        "720": 0.01,
    }

    stoploss = -0.04

    trailing_stop = False

    startup_candle_count = 210

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)
                & (dataframe["ema50"] > dataframe["ema200"])
                & (dataframe["close"] > dataframe["ema200"])
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] > 60)
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        return dataframe
