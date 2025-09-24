import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from trading_loop import trading_loop

from strategies.AbstractStrategy import AbstractStrategy

class StrategyManager:
    def __init__(self, strategy: AbstractStrategy):
        self.strategy = strategy
        self._stop_event = asyncio.Event()
        self._task = None
        self._start_time = None
        self._end_time = None

    async def start(self):
        if self._task and not self._task.done():
            return f"Strategy {self.strategy.__class__.__name__} is already running."
        self._stop_event.clear()
        self._task = asyncio.create_task(trading_loop(self.strategy, self._stop_event))
        self._start_time = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
        return f"Strategy {self.strategy.__class__.__name__} started."

    async def stop(self):
        if not self._task or self._task.done():
            return f"Strategy {self.strategy.__class__.__name__} is not running."
        self._stop_event.set()
        await self._task
        self._end_time = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")
        return f"Strategy {self.strategy.__class__.__name__} stopped."

    async def status(self):
        if self._task and not self._task.done():
            return f"Strategy {self.strategy.__class__.__name__} is running. Started on {self._start_time}."
        return f"Strategy {self.strategy.__class__.__name__} is not running. Last stopped on {self._end_time}."

    async def _run(self):
        while not self._stop_event.is_set():
            self.strategy.execute()
            await asyncio.sleep(5)  # Adjust sleep time as needed
