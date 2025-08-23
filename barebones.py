import ccxt
import pandas as pd
import time
import datetime
import requests
from zoneinfo import ZoneInfo

symbol = "ETH/USDT"
timeframe = "5m"
rsi_period = 14
paper_balance = {"USDT": 1000.0, "ETH": 0.25} 
# not really doing anyting with this yet, but plan is to use this with pandas eventually
transaction_log = []

# Initialize Kraken Client through ccxt, add API key if actually trading later
exchange = ccxt.kraken({
    "enableRateLimit": True
})

# TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
# CHAT_ID = "YOUR_CHAT_ID"

# def send_telegram(message: str):
#     if TELEGRAM_TOKEN and CHAT_ID:
#         url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
#         requests.post(url, data={"chat_id": CHAT_ID, "text": message})

def fetch_ohlcv():
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
    df["close"] = df["close"].astype(float)
    return df

def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def account_dollar_value(eth_price):
    eth_value = paper_balance["ETH"] * eth_price
    return round((paper_balance["USDT"] + eth_value), 2)

def log_transaction(price, amount, transaction_type):
    msg = f"INVALID transaction data received. Args: {price}, {amount}, {transaction_type}"
    now = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
    if transaction_type == "BUY": 
        transaction_log.append({"eth_price": price, "amount_purchased": amount, "account_dollar_value": account_dollar_value(price)})
        msg = f"[{now}]:BUY {amount:.5f} ETH @ {price:.2f} | Balances: USDT:{paper_balance['USDT']:.2f} ETH:{paper_balance['ETH']:.5f} Total:{account_dollar_value(price)}"
    elif transaction_type == "SELL":
        transaction_log.append({"eth_price": price, "amount_sold": amount, "account_dollar_value": account_dollar_value(price)})
        msg = f"[{now}]SELL {amount:.5f} ETH @ {price:.2f} | Balances: USDT:{paper_balance['USDT']:.2f} ETH:{paper_balance['ETH']:.5f} Total:{account_dollar_value(price)}"
    print(msg)


def paper_buy(price, amount):
    global paper_balance
    cost = price * amount
    if paper_balance["USDT"] >= cost:
        paper_balance["USDT"] -= cost
        paper_balance["ETH"] += amount
        log_transaction(price, amount, "BUY")
        # send_telegram(msg)

def paper_sell(price, amount):
    global paper_balance
    if paper_balance["ETH"] >= amount:
        paper_balance["ETH"] -= amount
        paper_balance["USDT"] += price * amount
        log_transaction(price, amount, "SELL")
        # send_telegram(msg)

# print the ETH price on startup for a baseline
print(f"Initial Balances: USDT:{paper_balance['USDT']:.2f} ETH:{paper_balance['ETH']:.5f} Total:{account_dollar_value(fetch_ohlcv()['close'].iloc[-1])}")
# execution loop
while True:
    df = fetch_ohlcv()
    df["rsi"] = compute_rsi(df["close"], rsi_period)
    latest_rsi = df["rsi"].iloc[-1]
    latest_price = df["close"].iloc[-1]
    now = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{now}] Price={latest_price}, RSI={latest_rsi:.2f}")

    # Strategy: Buy if RSI < 35, Sell if RSI > 65
    trade_size = 0.01  
    if latest_rsi < 35:
        paper_buy(latest_price, trade_size)
    elif latest_rsi > 65:
        paper_sell(latest_price, trade_size)

    time.sleep(60) 

