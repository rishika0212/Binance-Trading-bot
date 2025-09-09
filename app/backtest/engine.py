from typing import List, Dict

class Backtester:
    def __init__(self, strategy):
        self.strategy = strategy

    def run(self, symbol: str, bars: List[Dict]):
        equity = 0.0
        position = 0.0
        last_price = None
        trades = []
        for bar in bars:
            last_price = bar['close']
            sig = self.strategy.on_bar_close(symbol, bar)
            if not sig:
                continue
            if sig['signal'] == 'LONG' and position <= 0:
                # enter long 1 unit for simplicity
                position = 1.0
                trades.append({'action': 'BUY', 'price': last_price})
            elif sig['signal'] == 'FLAT' and position > 0:
                # exit to flat
                position = 0.0
                trades.append({'action': 'SELL', 'price': last_price})
        return {'equity': equity, 'trades': trades}