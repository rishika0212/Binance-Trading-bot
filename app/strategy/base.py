class Strategy:
    def on_bar_close(self, symbol: str, ohlc):
        """Return a signal dict or None. ohlc: {'open','high','low','close','volume'}"""
        raise NotImplementedError