from collections import deque
from .base import Strategy

class SMACrossover(Strategy):
    def __init__(self, fast=20, slow=50):
        self.fast = fast
        self.slow = slow
        self.buf = {}

    def on_bar_close(self, symbol, ohlc):
        close = float(ohlc['close'])
        d = self.buf.setdefault(symbol, {'fast': deque(maxlen=self.fast), 'slow': deque(maxlen=self.slow)})
        d['fast'].append(close)
        d['slow'].append(close)
        if len(d['fast']) == self.fast and len(d['slow']) == self.slow:
            f = sum(d['fast'])/self.fast
            s = sum(d['slow'])/self.slow
            if f > s:
                return {'symbol': symbol, 'signal': 'LONG'}
            if f < s:
                return {'symbol': symbol, 'signal': 'FLAT'}
        return None