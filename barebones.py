import asyncio
import ccxt
import datetime
import os
import pandas as pd
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from zoneinfo import ZoneInfo

symbol = "ETH/USDT"
# if we are polling every minute, should we have the timeframe match? 
timeframe = "5m"
rsi_period = 14
paper_balance = {"USDT": 1000.0, "ETH": 0.25} 
# may do more detailed logging for analysis with pandas later, for now this just tracks buys/sells
transaction_log = []
current_rsi = 0.0
current_eth_price = 0.0

# Initialize Kraken Client through ccxt, add API key if actually trading later
exchange = ccxt.kraken({
    "enableRateLimit": True
})

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # optional; will be set on /start
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_telegram(message: str):
    url = f"{BASE_URL}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print(f"Telegram send error: {e}")

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

def current_potential_eth(eth_price):
    dollars_as_eth = paper_balance["USDT"] / eth_price
    return round(paper_balance["ETH"] + dollars_as_eth, 5)

def log_transaction(price, amount, transaction_type):
    msg = f"INVALID transaction data received. Args: {price}, {amount}, {transaction_type}"
    now = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
    if transaction_type == "BUY": 
        # transaction_log.append({"eth_price": price, "amount_purchased": amount, "account_dollar_value": account_dollar_value(price)})
        msg = f"[{now}]:BUY {amount:.5f} ETH @ {price:.2f} | Balances: USDT:{paper_balance['USDT']:.2f} ETH:{paper_balance['ETH']:.5f} Total:{account_dollar_value(price)}"
    elif transaction_type == "SELL":
        # transaction_log.append({"eth_price": price, "amount_sold": amount, "account_dollar_value": account_dollar_value(price)})
        msg = f"[{now}]SELL {amount:.5f} ETH @ {price:.2f} | Balances: USDT:{paper_balance['USDT']:.2f} ETH:{paper_balance['ETH']:.5f} Total:{account_dollar_value(price)}"
    transaction_log.append(msg)
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

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    await update.message.reply_text("Bot is running! Use /rsi to check RSI, /balance for balances.")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "/start - initialize the service\n"
        "/help - displays this message\n"
        "/balances - displays USDT and ETH balances\n"
        "/recent - shows the last five transactions, if any\n"
        "/rsi - returns the current RSI for ETH\n"
    )
    await update.message.reply_text(msg)

async def balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"Balances:\nUSDT: {paper_balance['USDT']:.2f}\nETH: {paper_balance['ETH']:.5f}"
    await update.message.reply_text(msg)

async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Recent trades:\n" + "\n".join(transaction_log[-5:])
    await update.message.reply_text(msg)

async def rsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = fetch_ohlcv()
    df["rsi"] = compute_rsi(df["close"], rsi_period)
    latest_rsi = df["rsi"].iloc[-1]
    await update.message.reply_text(f"Current RSI: {latest_rsi:.2f}")

# TODO: 
# See errorlog.txt, need error handling for API requests, initiate a wait and retry 
async def trading_loop(app: Application, stop_event: asyncio.Event):
    first_loop = True
    lookback_frames = 5
    # Don't allow a trade until we have enough frames to do trend analysis
    last_trade_time = datetime.datetime.now(ZoneInfo("America/Los_Angeles")) - datetime.timedelta(minutes=lookback_frames)
    cooldown_minutes = 15
    trade_size = 0.01

    try: 
        while not stop_event.is_set():
            df = fetch_ohlcv()
            df["rsi"] = compute_rsi(df["close"], rsi_period)
            current_rsi = df["rsi"].iloc[-1]
            current_eth_price = df["close"].iloc[-1]
            now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
            log_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            if first_loop:
                print(f"[{log_timestamp}]: Startup Balances:")
                print(f"Initial USDT: {paper_balance['USDT']:.2f}")
                print(f"Initial ETH: {paper_balance['ETH']:.5f}")
                print(f"Total Dollar Value: {account_dollar_value(current_eth_price)}")
                print(f"Total ETH Potential: {current_potential_eth(current_eth_price)}")
                first_loop = False
            else: 
                print(f"[{log_timestamp}] Price={current_eth_price}, RSI={current_rsi:.2f}")

            can_trade = (
                last_trade_time is None or 
                (now - last_trade_time).total_seconds() / 60 > cooldown_minutes
            )

            if can_trade:
                recent_rsi = df["rsi"].iloc[-lookback_frames:]
                uptrend = recent_rsi.is_monotonic_increasing
                downtrend = recent_rsi.is_monotonic_decreasing

                if downtrend and current_rsi < 30:
                    paper_buy(current_eth_price, trade_size)
                elif uptrend and current_rsi > 70:
                    paper_sell(current_eth_price, trade_size)

            for _ in range(60):
                if stop_event.is_set():
                    break
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        print("Trading loop cancelled")


async def main():
    stop_event = asyncio.Event()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("rsi", rsi))
    app.add_handler(CommandHandler("balances", balances))
    app.add_handler(CommandHandler("recent", recent))

    trade_loop_task = asyncio.create_task(trading_loop(app, stop_event))

    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling()
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Ctrl+C pressed — stopping bot")
    finally:
        stop_event.set()
        trade_loop_task.cancel()
        try:
            await trade_loop_task
        except asyncio.CancelledError:
            pass

        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("Bot shut down cleanly")

if __name__ == "__main__":
    asyncio.run(main())