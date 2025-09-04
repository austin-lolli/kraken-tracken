import asyncio
import ccxt
import datetime
import os
import pandas as pd
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from zoneinfo import ZoneInfo

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # optional; will be set on /start
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

class LiveStrategy():
    def __init__(self, strategy):
        self.strategy = strategy
        self.token = "ETH"
        self.paper_balance = {"USDT": 1000.0, "ETH": 0.25} 
        self.transaction_log = []

    def send_telegram(message: str):
        url = f"{BASE_URL}/sendMessage"
        try:
            requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        except Exception as e:
            print(f"Telegram send error: {e}")

    def account_dollar_value(self, eth_price):
        eth_value = self.paper_balance[self.token] * eth_price
        return round((self.paper_balance["USDT"] + eth_value), 2)

    def current_potential_eth(self, eth_price):
        dollars_as_eth = self.paper_balance["USDT"] / eth_price
        return round(self.paper_balance[self.token] + dollars_as_eth, 5)

    def log_transaction(self, price, amount, transaction_type):
        msg = f"INVALID transaction data received. Args: {price}, {amount}, {transaction_type}"
        now = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
        # TODO: make a balances string function to use for trade loop and post transaction balance reporting
        if transaction_type == "BUY": 
            msg = (f"[{now}]:BUY {amount:.5f} {self.token} @ {price:.2f}\n" 
                    + f"Balances: USDT:{self.paper_balance['USDT']:.2f} {self.token}:{self.paper_balance[self.token]:.5f}\n"
                    + f"Total:{self.account_dollar_value(price)}\n")
        elif transaction_type == "SELL":
            msg = (f"[{now}]:SELL {amount:.5f} {self.token} @ {price:.2f}\n" 
                    + f"Balances: USDT:{self.paper_balance['USDT']:.2f} {self.token}:{self.paper_balance[self.token]:.5f}\n"
                    + f"Total:{self.account_dollar_value(price)}\n")
        # TODO: Store Pandas data frames in transaction log instead of logging strings
        self.transaction_log.append(msg)
        print(msg)

    def paper_buy(self, price, amount):
        cost = price * amount
        if self.paper_balance["USDT"] >= cost:
            self.paper_balance["USDT"] -= cost
            self.paper_balance[self.token] += amount
            self.log_transaction(price, amount, "BUY")

    def paper_sell(self, price, amount):
        if self.paper_balance[self.token] >= amount:
            self.paper_balance[self.token] -= amount
            self.paper_balance["USDT"] += price * amount
            self.log_transaction(price, amount, "SELL")

    # --- Telegram Handlers ---
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.CHAT_ID = update.effective_chat.id
        await update.message.reply_text("Bot is running! Use /help to see list of commands.")

    async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = (
            "/start - initialize the service\n"
            "/help - displays this message\n"
            "/balances - displays USDT and ETH balances\n"
            "/recent <number> - shows the last <number> transactions, if any. Default <number> is 5.\n"
            "/rsi - returns the current RSI for ETH\n"
        )
        await update.message.reply_text(msg)

    async def balances(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = f"Balances:\nUSDT: {self.paper_balance['USDT']:.2f}\nETH: {self.paper_balance['ETH']:.5f}"
        await update.message.reply_text(msg)

    async def recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        num_trades = 5

        if context.args:
            try:
                num_trades = int(context.args[0])
            except ValueError:
                await update.message.reply_text("Please provide a valid number.")
                return

        msg = "Recent trades:\n" + "\n".join(self.transaction_log[-num_trades:]) +f"\nLast {num_trades} shown of {len(self.transaction_log)} transactions."
        await update.message.reply_text(msg)

    async def rsi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # TODO: Condiser having the compute_rsi function in AbstractStrat just call OHLCV on its own
        df = self.strategy.fetch_ohlcv()
        df["rsi"] = self.strategy.compute_rsi(df["close"])
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
                if first_loop:
                    print(f"[{log_timestamp}]: Startup Balances:")
                    print(f"Initial USDT: {paper_balance['USDT']:.2f}")
                    print(f"Initial ETH: {paper_balance['ETH']:.5f}")
                    print(f"Total Dollar Value: {account_dollar_value(current_eth_price)}")
                    print(f"Total ETH Potential: {current_potential_eth(current_eth_price)}")
                    first_loop = False

                df = fetch_ohlcv()
                df["rsi"] = compute_rsi(df["close"])
                current_rsi = df["rsi"].iloc[-1]
                current_eth_price = df["close"].iloc[-1]
                now = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
                log_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

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
                        last_trade_time = now
                    elif uptrend and current_rsi > 70:
                        paper_sell(current_eth_price, trade_size)
                        last_trade_time = now

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