from binance import ThreadedWebsocketManager
from threading import Lock

class PriceFeed:
    def __init__(self, api_key: str, api_secret: str, testnet: bool, logger):
        self.logger = logger
        self.twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret, testnet=testnet)
        self.latest = {}
        self._lock = Lock()

    def start(self, symbols):
        self.twm.start()
        for s in symbols:
            self.twm.start_symbol_ticker_socket(callback=self._on_ticker, symbol=s)

    def _on_ticker(self, msg):
        try:
            symbol = msg['s']
            price = float(msg['c'])
            with self._lock:
                self.latest[symbol] = price
        except Exception as e:
            self.logger.error(f"WS parse error: {e}")

    def get_price(self, symbol):
        with self._lock:
            return self.latest.get(symbol)

    def stop(self):
        try:
            self.twm.stop()
        except Exception:
            pass