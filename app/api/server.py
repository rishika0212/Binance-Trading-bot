from flask import Flask, jsonify

class Services:
    def __init__(self, price_feed=None):
        self.price_feed = price_feed


def create_app(services: Services):
    app = Flask(__name__)

    @app.get('/health')
    def health():
        return jsonify({'ok': True})

    @app.get('/prices/<symbol>')
    def price(symbol):
        price = services.price_feed.get_price(symbol) if services.price_feed else None
        return jsonify({'symbol': symbol, 'price': price})

    return app