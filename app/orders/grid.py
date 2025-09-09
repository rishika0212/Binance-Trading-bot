from typing import Dict, Any, List

class GridTrader:
    """Simple grid: place layered limit buy/sell orders around a reference price."""

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    def build_grid(self, symbol: str, base_price: float, levels: int, step_pct: float, qty: str, side: str) -> Dict[str, Any]:
        try:
            orders: List[Dict] = []
            for i in range(1, levels + 1):
                if side.upper() == 'BUY':
                    price = base_price * (1 - step_pct * i)
                    order = self.client.create_order(
                        symbol=symbol, side='BUY', type='LIMIT', timeInForce='GTC',
                        quantity=qty, price=str(price)
                    )
                else:
                    price = base_price * (1 + step_pct * i)
                    order = self.client.create_order(
                        symbol=symbol, side='SELL', type='LIMIT', timeInForce='GTC',
                        quantity=qty, price=str(price)
                    )
                orders.append(order)
            return {'success': True, 'orders': orders}
        except Exception as e:
            self.logger.error(f"Grid build failed: {e}")
            return {'success': False, 'error': str(e)}