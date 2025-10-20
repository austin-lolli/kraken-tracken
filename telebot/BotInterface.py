import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from strategies.AbstractStrategy import AbstractStrategy

class BotInterface:
    CHAT_ID = os.getenv("CHAT_ID")
    MAX_MESSAGE_LENGTH = 4096

    def __init__(self, app: Application, strategies: dict[str, AbstractStrategy]):
        self.strategies = strategies
        self.register_handlers(app)

    # Message reply wrapper to split long messages
    async def _send_message(self, update: Update, message: str):
        message_chunks = [message[i:i + self.MAX_MESSAGE_LENGTH] for i in range(0, len(message), self.MAX_MESSAGE_LENGTH)]

        for chunk in message_chunks:
            try:
                await update.message.reply_text(chunk)
            except Exception as e:
                print(f"Error sending message chunk: {e}", file=sys.stderr)


    def register_handlers(self, app: Application):
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("strategy_start", self.strategy_start))
        app.add_handler(CommandHandler("strategy_stop", self.strategy_stop))
        app.add_handler(CommandHandler("strategy_status", self.strategy_status))
        app.add_handler(CommandHandler("get_strategies", self.get_strategies))
        app.add_handler(CommandHandler("rsi", self.rsi))
        app.add_handler(CommandHandler("balances", self.balances))
        app.add_handler(CommandHandler("recent", self.recent))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        CHAT_ID = update.effective_chat.id
        await self._send_message(update, "Kraken Tracken is running! Use /help to see available commands.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = (
            "General commands:\n"
            "   /start - initializes and starts running the service\n"
            "   /help - displays this message\n"
            # might have rsi and chart generation here
            "Strategy commands:\n"
            "   /get_strategies - lists all available strategies\n"
            "   /strategy_start <StrategyName> - starts the specified strategy\n"
            "   /strategy_stop <StrategyName> - stops the specified strategy\n"
            "   /strategy_status <StrategyName> - displays the status of the specified strategy\n"
            # These will need to take a strategy name argument
            "Deprecated (to be updated):\n"
            "   /balances <StrategyName>- displays USDT and ETH balances\n"
            "   /recent <StrategyName> <number> - shows the last <number> transactions, if any. Default <number> is 5.\n"
            "   /rsi - returns the current RSI for ETH\n"
        )
        await self._send_message(update, msg)

    async def strategy_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 1:
            await self._send_message(update, "Usage: /start_strategy <StrategyName>")
            return

        strategy_name = context.args[0]
        if strategy_name not in self.strategies:
            await self._send_message(update, f"Strategy {strategy_name} not found.")
        else:
            response = await self.strategies[strategy_name].start()
            await self._send_message(update, response)
        return
    
    async def strategy_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 1:
            await self._send_message(update, "Usage: /stop_strategy <StrategyName>")
            return

        strategy_name = context.args[0]
        if strategy_name not in self.strategies:
            await self._send_message(update, f"Strategy {strategy_name} not found.")
        else:
            response = await self.strategies[strategy_name].stop()
            await self._send_message(update, response)
        return

    async def strategy_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 1:
            await self._send_message(update, "Usage: /status_strategy <StrategyName>")
            return

        strategy_name = context.args[0]
        if strategy_name not in self.strategies:
            await self._send_message(update, f"Strategy {strategy_name} not found.")
        else:
            response = await self.strategies[strategy_name].status()
            await self._send_message(update, response)
        return

    async def get_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        strategy_list = "\n".join(self.strategies.keys())
        await self._send_message(update, f"Available strategies:\n{strategy_list}")

    # Note: I think we will either call the underlying strategy manager's strategy's function?
    async def balances(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 1:
            await self._send_message(update, "Usage: /balances <StrategyName>")
            return

        strategy_name = context.args[0]
        if strategy_name not in self.strategies:
            await self._send_message(update, f"Strategy {strategy_name} not found.")
        else:
            await self._send_message(update, str(self.strategies[strategy_name].strategy.get_balances()))

    async def recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) > 2 or len(context.args) < 1:
            await self._send_message(update, "Usage: /recent <StrategyName> <number>")
            return

        strategy_name = context.args[0]
        num_trades = 5 if len(context.args) == 1 else int(context.args[1])

        await self._send_message(update, self.strategies[strategy_name].strategy.get_recent_transactions(num_trades))

    # TODO: This is tied to a strategy but this should exist independently, similar to a chart
    async def rsi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 1:
            await self._send_message(update, "Usage: /rsi <StrategyName>")
            return

        strategy_name = context.args[0]
        await self._send_message(update, f"Current RSI: {self.strategies[strategy_name].strategy.compute_rsi()}")
