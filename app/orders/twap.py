import time
from typing import Dict, Any, Optional

class TWAPExecutor:
    """Execute a target quantity over a duration, splitting into slices at fixed interval."""

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    def execute(self, symbol: str, side: str, total_qty: float, duration_sec: int, slices: int, min_slice_qty: float = 0.0) -> Dict[str, Any]:
        if slices <= 0 or duration_sec <= 0:
            return {'success': False, 'error': 'Invalid slices/duration'}
        interval = duration_sec / slices
        slice_qty = max(total_qty / slices, min_slice_qty)
        placed = []
        for i in range(slices):
            try:
                order = self.client.create_order(
                    symbol=symbol, side=side.upper(), type='MARKET', quantity=str(slice_qty)
                )
                placed.append(order)
                self.logger.info(f"TWAP slice {i+1}/{slices} placed: {order.get('orderId')}")
            except Exception as e:
                self.logger.error(f"TWAP slice {i+1} failed: {e}")
                return {'success': False, 'placed': placed, 'error': str(e)}
            time.sleep(interval)
        return {'success': True, 'placed': placed}