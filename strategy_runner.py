import asyncio
import ccxt
import os
from telegram.ext import Application

from RSIStrategyWithDelay import RSIStrategyWithDelay
from trading_loop import trading_loop
from TelgramBotInterface import TelegramBotInterface

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")


async def strategy_runner():
    print("initializing exchange and strategy")
    exchange = ccxt.kraken({"enableRateLimit": True})
    strategy = RSIStrategyWithDelay(exchange, delay_minutes=15)

    print("starting telegram bot")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    TelegramBotInterface(app, strategy)

    stop_event = asyncio.Event()
    trade_loop_task = app.create_task(trading_loop(strategy, stop_event))

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
    asyncio.run(strategy_runner())
