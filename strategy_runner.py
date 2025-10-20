import asyncio
import ccxt
import os
from telegram.ext import Application

from strategies.RSIStrategyWithDelay import RSIStrategyWithDelay
from strategies.RSIStrategySimple import RSIStrategySimple
from trading_loop import trading_loop
from telebot.BotInterface import BotInterface
from StrategyManager import StrategyManager

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")

# main execution loop
async def strategy_runner():
    # initialilze exchange, telegram bot, and strategy dictionary
    exchange = ccxt.kraken({"enableRateLimit": True})
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    strategies = {}

    # The strategy logic is wrapped in a StrategyManager to handle start/stop/status
    strategies["rsi"] = StrategyManager(RSIStrategySimple(exchange))
    strategies["rsi_delay"] = StrategyManager(RSIStrategyWithDelay(exchange, delay_minutes=15))

    # Telegram bot is given telegram app and the strategy dictionary
    BotInterface(app, strategies)

    stop_event = asyncio.Event()

    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling(poll_interval=3, timeout=15, bootstrap_retries=3)
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Ctrl+C pressed — stopping bot")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("Bot shut down cleanly")


if __name__ == "__main__":
    asyncio.run(strategy_runner())
