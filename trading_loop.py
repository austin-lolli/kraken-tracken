import asyncio

from strategies.AbstractStrategy import AbstractStrategy, Signal

async def trading_loop(strategy: AbstractStrategy, stop_event: asyncio.Event):
    trade_size = 0.05

    try: 
        while not stop_event.is_set():
            prices = strategy.get_ohlcv()
            signal = strategy.generate_signal(prices)
            latest_price = prices["close"].iloc[-1]

            if signal in [Signal.BUY, Signal.SELL]:
                strategy.perform_transaction(latest_price, trade_size, signal)

            await asyncio.sleep(60)
    
    except asyncio.CancelledError:
        print("Trading loop stopped.")