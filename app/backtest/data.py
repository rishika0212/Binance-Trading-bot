from typing import List, Dict
from binance import Client

class DataFetcher:
    def __init__(self, client: Client):
        self.client = client

    def klines(self, symbol: str, interval: str = Client.KLINE_INTERVAL_1MINUTE, limit: int = 500) -> List[Dict]:
        raw = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        out = []
        for k in raw:
            out.append({
                'open_time': k[0], 'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]), 'close': float(k[4]),
                'volume': float(k[5]), 'close_time': k[6]
            })
        return out