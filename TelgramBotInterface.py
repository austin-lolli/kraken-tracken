import AbstractStrategy
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

class TelegramBotInterface:
    CHAT_ID = os.getenv("CHAT_ID")

    def __init__(self, app: Application, strategy: AbstractStrategy):
        self.strategy = strategy
        self.register_handlers(app)

    def register_handlers(self, app: Application):
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("rsi", self.rsi))
        app.add_handler(CommandHandler("balances", self.balances))
        app.add_handler(CommandHandler("recent", self.recent))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        CHAT_ID = update.effective_chat.id
        # TODO: have the message include the strategy name
        await update.message.reply_text(f"{self.strategy.__class__.__name__} is running! Use /help to see available commands.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = (
            "/start - initialize the service\n"
            "/help - displays this message\n"
            "/balances - displays USDT and ETH balances\n"
            "/recent <number> - shows the last <number> transactions, if any. Default <number> is 5.\n"
            "/rsi - returns the current RSI for ETH\n"
        )
        await update.message.reply_text(msg)

    async def balances(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.strategy.get_balances())

    async def recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        num_trades = 5

        if context.args:
            try:
                num_trades = int(context.args[0])
            except ValueError:
                await update.message.reply_text("Invalid number provided for count. \nUsage: /recent <number> - shows last <number> transactions")
                return

        await update.message.reply_text(self.strategy.get_recent_transactions(num_trades))

    async def rsi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"Current RSI: {self.strategy.compute_rsi()}")
