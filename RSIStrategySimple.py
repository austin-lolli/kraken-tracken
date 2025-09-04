from AbstractStrategy import AbstractStrategy, Signal
import pandas as pd


class RSIStrategySimple(AbstractStrategy):
    def __init__(self, exchange, symbol="ETH/USDT", period=14, rsiLower=30, rsiUpper=70):
        super().__init__(symbol)
        self.exchange = exchange
        self.period = period
        self.rsiLower = rsiLower
        self.rsiUpper = rsiUpper

    def compute_rsi(self) -> float:
        delta = self.get_ohlcv()["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(self.period).mean()
        avg_loss = loss.rolling(self.period).mean()
        rs = avg_gain / avg_loss
        # last item in dataframe contains the 'current' RSI
        return round(100 - (100 / (1 + rs)).iloc[-1], 2)
    
    def generate_signal(self, df: pd.DataFrame) -> Signal:
        df['rsi'] = self.compute_rsi()
        latest_rsi = df['rsi'].iloc[-1]

        if latest_rsi < self.rsiLower:
            return Signal.BUY
        elif latest_rsi > self.rsiUpper:
            return Signal.SELL
        return Signal.HOLD
