# Bollinger-band squeeze breakout (volatility expansion).
#
# Idea: when volatility compresses (band width in the bottom quintile of its
# recent range), an expansion usually follows. Enter when price breaks above
# the upper band out of a squeeze, with a volume surge and a bull-regime
# filter. Exit when price loses the middle band, or via ROI/stop.

import talib.abstract as ta
from pandas import DataFrame

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class BbSqueezeStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False

    minimal_roi = {
        "0": 0.06,
        "240": 0.04,
        "720": 0.02,
    }

    stoploss = -0.04

    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.035
    trailing_only_offset_is_reached = True

    startup_candle_count = 310

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_middle"] = bollinger["mid"]
        dataframe["bb_upper"] = bollinger["upper"]
        dataframe["bb_width"] = (
            (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe["bb_middle"]
        )
        dataframe["bb_width_floor"] = dataframe["bb_width"].rolling(100).quantile(0.2)
        dataframe["in_squeeze"] = (
            dataframe["bb_width"] <= dataframe["bb_width_floor"]
        ).shift(1)
        dataframe["vol_ma"] = dataframe["volume"].rolling(20).mean()
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["in_squeeze"] == 1)
                & qtpylib.crossed_above(dataframe["close"], dataframe["bb_upper"])
                & (dataframe["volume"] > 1.5 * dataframe["vol_ma"])
                & (dataframe["close"] > dataframe["ema_trend"])
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                qtpylib.crossed_below(dataframe["close"], dataframe["bb_middle"])
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        return dataframe
