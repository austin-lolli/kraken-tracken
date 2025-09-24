from abc import ABC, abstractmethod
import ccxt
from enum import Enum
import pandas as pd
from zoneinfo import ZoneInfo
import datetime

class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class AbstractStrategy(ABC):
    def __init__(self, exchange, symbol="ETH/USDT", timeframe="5m"): 
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.balances = {"USDT": 1000.0, "ETH": 0.25}
        self.transactions = []

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Signal:
        pass

    def get_ohlcv(self):
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
        df["close"] = df["close"].astype(float)
        return df
    
    def get_balances(self):
        return self.balances
    
    def get_recent_transactions(self, count):
        if len(self.transactions) == 0:
            return "No transactions found."
        
        recent = self.transactions[-count:] if count < len(self.transactions) else self.transactions
        return "\n".join(recent)
    
    def perform_transaction(self, price: float, token_amount: float, action: Signal):
        now = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{now}][{action}]: {token_amount} ETH at ${price}"
        failure_message = f"[{now}][FAILURE]: Unable to {action} {token_amount} ETH at ${price}"

        transaction_value = float(round(price * token_amount, 2))
        token_amount = round(token_amount, 5)

        if action == Signal.BUY:
            if self.balances["USDT"] < transaction_value:
                message = failure_message
            else:
                self.balances["USDT"] = round(self.balances["USDT"] - transaction_value, 2)
                self.balances["ETH"] = round(self.balances["ETH"] + token_amount, 5)
        elif action == Signal.SELL:
            if self.balances["ETH"] < token_amount:
                message = failure_message
            else:
                self.balances["USDT"] = round(self.balances["USDT"] + transaction_value, 2)
                self.balances["ETH"] = round(self.balances["ETH"] - token_amount, 5)

        self.transactions.append(message)
        print(message)
