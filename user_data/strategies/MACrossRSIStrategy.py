"""
双均线交叉 + RSI 过滤策略
策略逻辑：
- 快线(短期均线) 上穿 慢线(长期均线) 且 RSI < 70 时买入
- 快线下穿慢线 或 RSI > 80 时卖出
"""

from freqtrade.strategy import IStrategy
import talib.abstract as ta
from pandas import DataFrame


class MACrossRSIStrategy(IStrategy):
    # 策略接口版本
    INTERFACE_VERSION = 3

    # 最小回报率（达到即止盈）
    minimal_roi = {
        "0": 0.15,     # 0分钟后，15% 止盈
        "360": 0.08,   # 6小时后，8% 止盈
        "720": 0.04,   # 12小时后，4% 止盈
        "1440": 0.02   # 24小时后，2% 止盈
    }

    # 止损
    stoploss = -0.08  # 8% 止损

    # 是否使用追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    # 时间周期
    timeframe = '1h'

    # 运行的合约数
    max_open_trades = 3

    # 每个交易的注资金额
    stake_amount = 'unlimited'

    # 是否允许做空
    can_short = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算所有技术指标"""
        # 双均线
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=12)   # 快线 12小时
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=26)   # 慢线 26小时

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # MACD (作为参考)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """买入信号"""
        # 条件1: 快线上穿慢线 (金叉)
        golden_cross = (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1))
        )

        # 条件2: RSI < 70 (避免超买时买入)
        rsi_ok = dataframe['rsi'] < 70

        # 条件3: 有成交量
        volume_ok = dataframe['volume'] > 0

        # 综合买入信号
        dataframe.loc[
            golden_cross & rsi_ok & volume_ok,
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """卖出信号"""
        # 条件1: 快线下穿慢线 (死叉)
        death_cross = (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
        )

        # 条件2: RSI > 80 (超买)
        rsi_overbought = dataframe['rsi'] > 80

        # 任一条件满足则卖出
        dataframe.loc[
            (death_cross | rsi_overbought),
            'exit_long'
        ] = 1

        return dataframe
