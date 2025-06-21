# Live Trading with Real-Time Data

This module adds real-time data capabilities to the options trading bot, allowing you to trade with live market data.

## Features

- Configurable data providers (Finnhub, Yahoo Finance)
- Real-time market data updates
- Live options trading signals
- Stop loss and take profit monitoring
- Position tracking and management
- State persistence and logging

## Data Providers

The bot supports multiple data providers through a pluggable architecture:

1. **Finnhub** - Real-time stock data with free API tier
2. **Yahoo Finance** - Near real-time data with no API key required

You can easily add more providers by implementing the `BaseDataProvider` interface.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API Keys

For Finnhub:
1. Create an account at [finnhub.io](https://finnhub.io/)
2. Get your API key from the dashboard

### 3. Configure the Bot

Create a configuration file or use the default configuration.

## Usage

### Basic Usage

Run the live trading bot with default settings:

```bash
python live_trading.py --api-key YOUR_FINNHUB_API_KEY
```

### Command Line Options

- `--symbols`: List of stock symbols to trade (e.g., `--symbols AAPL MSFT GOOGL`)
- `--config`: Path to strategy configuration file (e.g., `--config custom_strategy.json`)
- `--provider`: Data provider to use (`finnhub` or `yahoo`)
- `--api-key`: API key for the data provider
- `--interval`: Update interval in seconds (e.g., `--interval 30`)
- `--output-dir`: Directory to save output files

### Example

```bash
python live_trading.py --symbols AAPL MSFT --provider finnhub --api-key YOUR_API_KEY --interval 30 --config custom_strategy.json
```

## How It Works

1. **Initialization**:
   - The bot loads historical data for the specified symbols
   - Technical indicators are calculated
   - Initial options data is fetched

2. **Update Loop**:
   - Real-time data is fetched at the specified interval
   - Technical indicators are recalculated
   - New trading signals are generated
   - Positions are updated based on signals and risk management rules

3. **Risk Management**:
   - Stop loss and take profit levels are monitored in real-time
   - Positions are automatically closed when exit conditions are met
   - Maximum holding periods are enforced

4. **State Persistence**:
   - Current positions, signals, and market data are saved to disk
   - Detailed logs are maintained for analysis

## Output Files

The live trading bot generates several output files:

- `positions.json`: Current positions and their details
- `signals.json`: Latest trading signals
- `real_time_data.json`: Latest market data
- `live_trading.log`: Detailed log of all activities
- `{SYMBOL}_historical.csv`: Historical data for each symbol

## Switching Data Providers

To switch from Finnhub to Yahoo Finance:

```bash
python live_trading.py --provider yahoo
```

No API key is required for Yahoo Finance.

## Adding Custom Data Providers

1. Create a new provider class that inherits from `BaseDataProvider`
2. Implement the required methods
3. Add the provider to the `DataProviderFactory`

Example:

```python
class MyCustomProvider(BaseDataProvider):
    def initialize_client(self, **kwargs):
        # Initialize your API client
        pass
    
    def get_historical_data(self, symbol, period='3mo', interval='1d'):
        # Fetch historical data
        pass
    
    def get_real_time_data(self, symbol):
        # Fetch real-time data
        pass
    
    def get_options_chain(self, symbol):
        # Fetch options chain data
        pass
```

Then add it to the factory:

```python
if provider_name == 'mycustom':
    return MyCustomProvider(api_key=api_key, **kwargs)
```

## Disclaimer

This live trading bot is for educational and research purposes only. It is not intended to be used as financial advice or a recommendation to trade real money. Trading stocks and options involves risk, and you should always consult with a financial advisor before making investment decisions.
## Trading Platforms

The bot now supports multiple trading platforms through a pluggable architecture:

1. **Paper Trading** - Simulated trading with no real money
2. **Investopedia Simulator** - Practice trading using the Investopedia Stock Simulator

You can easily add more platforms by implementing the `BaseTradingPlatform` interface.

### Using Investopedia Simulator

To use the Investopedia Stock Simulator:

```bash
python live_trading.py --platform investopedia --username YOUR_USERNAME --password YOUR_PASSWORD
```

### Using Paper Trading

For simulated trading with no external dependencies:

```bash
python live_trading.py --platform paper
```

## Order Execution

The bot now includes an `OrderExecutor` component that:

1. Connects to the selected trading platform
2. Executes trades based on generated signals
3. Manages positions and monitors exit conditions
4. Tracks order history and execution details

### Configuration

You can configure order execution parameters in your strategy configuration:

```json
{
    "max_positions": 5,
    "position_size": 0.1,
    "enable_options": true,
    "enable_stocks": true
}
```

### Execution Log

All executed orders are logged to `execution_log.json` in the output directory, including:
- Order details
- Signal information
- Execution timestamp
- Trading platform used
## Multi-Provider Data Architecture

The bot now supports using different data providers for stocks and options:

### Stock Price Data (Finnhub)

Finnhub's free API provides:
- Real-time stock quotes (1-minute updates)
- 60 API calls per minute limit
- Basic technical indicators

To use Finnhub for stock data:

```bash
python live_trading.py --stock-provider finnhub --stock-api-key YOUR_FINNHUB_API_KEY
```

### Options Data (Polygon.io)

Polygon.io's free tier provides:
- Options reference data (strikes, expiration dates)
- Delayed options quotes
- 5 API calls per minute limit

To use Polygon.io for options data:

```bash
python live_trading.py --options-provider polygon --options-api-key YOUR_POLYGON_API_KEY
```

### Using Both Providers Together

For the optimal setup, use both providers together:

```bash
python live_trading.py \
  --stock-provider finnhub --stock-api-key YOUR_FINNHUB_API_KEY \
  --options-provider polygon --options-api-key YOUR_POLYGON_API_KEY
```

### Fallback to Yahoo Finance

If you don't have API keys, the bot will fall back to Yahoo Finance:

```bash
python live_trading.py --stock-provider yahoo --options-provider yahoo
```

## Data Provider Architecture

The `MultiProviderHandler` manages data from multiple providers:
- Routes stock data requests to the stock provider
- Routes options data requests to the options provider
- Handles rate limiting and error recovery
- Provides a unified interface for the trading bot
## Investopedia Authentication Update

The bot now supports Investopedia's passwordless authentication using bearer tokens:

### Using Bearer Token Authentication

```bash
python live_trading.py --platform investopedia --auth-token YOUR_BEARER_TOKEN
```

To obtain your bearer token:

1. Log in to Investopedia Simulator in your browser
2. Open browser developer tools (F12)
3. Go to the Network tab
4. Refresh the page
5. Look for requests to investopedia.com
6. Find the "Authorization" header with "Bearer" token
7. Copy the token value (without the "Bearer" prefix)

### Legacy Authentication

The bot still supports username/password authentication for backward compatibility:

```bash
python live_trading.py --platform investopedia --username YOUR_USERNAME --password YOUR_PASSWORD
```

However, this method may not work if Investopedia has fully transitioned to passwordless authentication.
