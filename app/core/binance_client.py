import logging
from typing import Optional
from binance import Client

class BinanceClientFactory:
    """Creates a configured python-binance Client with robust futures testnet URLs."""

    @staticmethod
    def create(api_key: str, api_secret: str, testnet: bool = True, logger: Optional[logging.Logger] = None) -> Client:
        client = Client(api_key, api_secret, testnet=testnet)
        if testnet:
            BinanceClientFactory._force_testnet_futures_urls(client, logger)
        return client

    @staticmethod
    def _force_testnet_futures_urls(client: Client, logger: Optional[logging.Logger]):
        base = 'https://testnet.binancefuture.com'
        for attr in (
            'FUTURES_URL', 'futures_url', 'futures_api_url', 'UM_FUTURES_URL', 'UMFUTURES_URL'
        ):
            if hasattr(client, attr):
                try:
                    setattr(client, attr, base)
                except Exception as e:
                    if logger:
                        logger.debug(f"Ignoring error setting {attr}: {e}")