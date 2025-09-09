from typing import Dict, Any

class OCOManager:
    """OCO manager: prefers native Binance OCO; falls back to client-side TP/SL pair."""

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger

    def submit(self, symbol: str, side: str, qty: str, tp_price: str, sl_price: str) -> Dict[str, Any]:
        exit_side = 'SELL' if side.upper() == 'BUY' else 'BUY'
        # Try native OCO first (Spot)
        try:
            if hasattr(self.client, 'create_oco_order'):
                oco = self.client.create_oco_order(
                    symbol=symbol,
                    side=exit_side,
                    quantity=qty,
                    price=tp_price,              # TP limit price
                    stopPrice=sl_price,          # SL trigger
                    stopLimitPrice=sl_price,     # SL limit
                    stopLimitTimeInForce='GTC'
                )
                return {'success': True, 'oco': oco, 'mode': 'native'}
        except Exception as ne:
            self.logger.warning(f"Native OCO failed, falling back to client-side: {ne}")
        # Fallback: place TP and SL as two separate orders
        try:
            tp = self.client.create_order(
                symbol=symbol, side=exit_side, type='LIMIT', timeInForce='GTC',
                quantity=qty, price=tp_price
            )
            sl = self.client.create_order(
                symbol=symbol, side=exit_side, type='STOP_LOSS_LIMIT', timeInForce='GTC',
                quantity=qty, price=sl_price, stopPrice=sl_price
            )
            return {'success': True, 'tp': tp, 'sl': sl, 'mode': 'client'}
        except Exception as e:
            self.logger.error(f"OCO submit failed: {e}")
            return {'success': False, 'error': str(e)}