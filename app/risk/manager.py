class RiskManager:
    def __init__(self, max_risk_usdt=50.0, stop_loss_pct=0.01):
        self.max_risk_usdt = max_risk_usdt
        self.stop_loss_pct = stop_loss_pct

    def size_position(self, price: float) -> float:
        # Qty = risk / (price * stop_loss_pct)
        if price <= 0:
            return 0.0
        qty = self.max_risk_usdt / (price * self.stop_loss_pct)
        return max(qty, 0.001)