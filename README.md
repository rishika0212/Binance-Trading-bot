# Binance Trading Bot

A modular cryptocurrency trading bot for Binance with support for spot trading, advanced order types, real-time price feeds, and backtesting capabilities.

## Features

- 🤖 **Core Trading Operations**
  - Market orders
  - Limit orders
  - Stop-limit orders
  - Order status tracking
  - Position management

- 📊 **Advanced Order Types**
  - OCO (One-Cancels-Other) orders
  - TWAP (Time-Weighted Average Price) execution
  - Grid trading strategy

- 📈 **Market Data**
  - Real-time WebSocket price feeds
  - Historical data fetching
  - OHLCV candlestick data

- 🔧 **Trading Strategies**
  - SMA crossover strategy included
  - Extensible strategy framework
  - Backtesting engine

- 🛡️ **Risk Management**
  - Position sizing
  - Stop-loss management
  - Account balance tracking

- 🗄️ **Data Storage**
  - SQLite database for order history
  - Trade logging
  - Performance tracking

- 🌐 **API Integration**
  - REST API server using Flask
  - WebSocket market data feeds
  - Comprehensive error handling

## Installation

1. Clone the repository:
```sh
git clone <repository-url>
cd trading-bot
```

2. Install required packages:
```sh
pip install -r requirements.txt
```

3. Create a `.env` file with your Binance API credentials:
```sh
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

## Project Structure

- `trading_bot.py` - Main bot implementation
- `test_bot.py` - Test suite for verifying functionality
- `app/`
  - `api/` - Flask REST API server
  - `backtest/` - Backtesting engine and data management
  - `core/` - Core exchange client functionality
  - `market/` - Market data and WebSocket feeds
  - `orders/` - Advanced order type implementations
  - `risk/` - Risk management utilities
  - `storage/` - Database and persistence layer
  - `strategy/` - Trading strategy implementations

## Usage

### Basic Bot Operation

1. Run the interactive bot:
```sh
python trading_bot.py
```

2. Run the test suite:
```sh
python test_bot.py
```

### Available Commands

The bot provides an interactive menu with the following options:

1. Place Market Order
2. Place Limit Order
3. Place Stop-Limit Order
4. Check Order Status
5. Cancel Order
6. Check Account Balance
7. Exit
8. OCO: Attach TP/SL
9. TWAP: Execute over time
10. Grid: Build grid around price
11. WS: Start live prices
12. WS: Show latest prices
13. API: Start Flask server
14. Backtest: SMA crossover

## Configuration

The bot supports both command-line arguments and environment variables:

```sh
python trading_bot.py --api-key YOUR_KEY --api-secret YOUR_SECRET --testnet
```

Environment variables:
- `BINANCE_API_KEY`: Your Binance API key
- `BINANCE_API_SECRET`: Your Binance API secret

## Testing

The `test_bot.py` script provides comprehensive testing:

1. Full functionality test
2. Generate sample config file
3. Quick connection test

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[Add your chosen license]

## Disclaimer

This bot is for educational purposes only. Use at your own risk. Always test with paper trading before using real funds.