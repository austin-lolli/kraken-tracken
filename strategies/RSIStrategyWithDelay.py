from strategies.AbstractStrategy import Signal
from strategies.RSIStrategySimple import RSIStrategySimple
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd


class RSIStrategyWithDelay(RSIStrategySimple):
    def __init__(self, exchange, symbol="ETH/USDT", period=14, rsi_lower=30, rsi_upper=70, delay_minutes=15):
        super().__init__(exchange, symbol, period, rsi_lower, rsi_upper)
        self.delay_minutes = delay_minutes
        self.last_trx_timestamp = datetime.now(ZoneInfo("America/Los_Angeles"))

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        df['rsi'] = self.compute_rsi()
        latest_rsi = df['rsi'].iloc[-1]
        now = datetime.now(ZoneInfo("America/Los_Angeles"))

        if now < self.last_trx_timestamp + timedelta(minutes=5):
            return Signal.HOLD
        elif latest_rsi < self.rsi_lower:
            self.last_trx_timestamp = now
            return Signal.BUY
        elif latest_rsi > self.rsi_upper:
            self.last_trx_timestamp = now
            return Signal.SELL
        return Signal.HOLD
