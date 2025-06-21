#!/usr/bin/env python3
"""
Live Trading Module
----------------
Entry point for live trading with real-time data
"""

import os
import sys
import logging
import argparse
import pandas as pd
import time
from datetime import datetime
import json

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_handler import DataHandler
from options_handler import OptionsHandler
from options_strategy import OptionsStrategy
from real_time_handler import RealTimeHandler
from multi_provider_handler import MultiProviderHandler
from order_executor import OrderExecutor
from strategy_config import load_strategy_config
from visualization import Visualizer

# Create output directory for generated files
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure logging
log_file = os.path.join(OUTPUT_DIR, "live_trading.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('live_trading')

class LiveTradingBot:
    def __init__(self, symbols, config_path=None, stock_provider='finnhub', options_provider='polygon',
                 stock_api_key=None, options_api_key=None, update_interval=60, output_dir=OUTPUT_DIR, 
                 trading_platform='paper', username=None, password=None, auth_token=None):
        """
        Initialize the live trading bot
        
        Args:
            symbols (list): List of stock symbols to trade
            config_path (str): Path to strategy configuration file
            stock_provider (str): Name of the stock data provider
            options_provider (str): Name of the options data provider
            stock_api_key (str): API key for the stock data provider
            options_api_key (str): API key for the options data provider
            update_interval (int): Interval in seconds between data updates
            output_dir (str): Directory to save output files
            trading_platform (str): Name of the trading platform
            username (str): Username for the trading platform (legacy)
            password (str): Password for the trading platform (legacy)
            auth_token (str): Authentication bearer token for trading platform
        """
        self.symbols = symbols
        self.config_path = config_path
        self.stock_provider = stock_provider
        self.options_provider = options_provider
        self.stock_api_key = stock_api_key
        self.options_api_key = options_api_key
        self.update_interval = update_interval
        self.output_dir = output_dir
        self.trading_platform = trading_platform
        self.auth_token = auth_token
        
        # Load strategy configuration
        self.config = load_strategy_config(config_path)
        
        # Initialize components
        self.data_handler = DataHandler()
        self.options_handler = OptionsHandler()
        self.options_strategy = OptionsStrategy(config_path)
        self.visualizer = Visualizer()
        
        # Initialize multi-provider data handler
        self.data_provider = MultiProviderHandler(
            stock_provider=stock_provider,
            options_provider=options_provider,
            stock_api_key=stock_api_key,
            options_api_key=options_api_key,
            update_interval=update_interval
        )
        
        # Initialize order executor
        self.order_executor = OrderExecutor(
            platform_name=trading_platform,
            config_path=config_path,
            output_dir=output_dir,
            username=username,
            password=password,
            auth_token=auth_token
        )
        
        # Data containers
        self.historical_data = {}
        self.real_time_data = {}
        self.options_data = {}
        self.signals = {}
        self.options_signals = {}
        self.positions = {}
        self.executed_orders = {}
        
        # Initialize positions
        for symbol in symbols:
            self.positions[symbol] = {
                'position': 0,
                'entry_price': 0,
                'entry_time': None,
                'strategy': None,
                'stop_loss': 0,
                'take_profit': 0
            }
        
        logger.info(f"Live trading bot initialized with {stock_provider} for stocks, {options_provider} for options, and {trading_platform} trading platform")
    
    def initialize(self, period='3mo', interval='1d'):
        """
        Initialize the bot with historical data
        
        Args:
            period (str): Time period for historical data
            interval (str): Data interval for historical data
        """
        logger.info("Initializing live trading bot")
        
        # Initialize historical data
        self.historical_data = self.data_provider.initialize_data(self.symbols, period, interval)
        
        # Calculate technical indicators
        for symbol in self.symbols:
            if symbol in self.historical_data and not self.historical_data[symbol].empty:
                self.historical_data[symbol] = self.data_handler.calculate_indicators(symbol, self.historical_data[symbol])
        
        # Update real-time data
        self.real_time_data = self.data_provider.update_real_time_data(self.symbols)
        
        # Update options data
        self.options_data = self.data_provider.update_options_data(self.symbols)
        
        # Get current positions from trading platform
        platform_positions = self.order_executor.get_positions()
        logger.info(f"Retrieved {len(platform_positions)} positions from trading platform")
        
        logger.info("Live trading bot initialization complete")
    
    def process_data_update(self, historical_data, real_time_data, options_data):
        """
        Process data update from data provider
        
        Args:
            historical_data (dict): Updated historical data
            real_time_data (dict): Updated real-time data
            options_data (dict): Updated options data
        """
        logger.info("Processing data update")
        
        # Update our data containers
        self.historical_data = historical_data
        self.real_time_data = real_time_data
        self.options_data = options_data
        
        # Recalculate technical indicators
        for symbol in self.symbols:
            if symbol in self.historical_data and not self.historical_data[symbol].empty:
                self.historical_data[symbol] = self.data_handler.calculate_indicators(symbol, self.historical_data[symbol])
        
        # Generate options trading signals
        self.options_signals = self.options_strategy.generate_signals(self.historical_data, self.options_data)
        
        # Execute trades based on signals
        self._execute_trades()
        
        # Save current state
        self._save_state()
    
    def _execute_trades(self):
        """Execute trades based on signals"""
        # Process signals and execute orders
        executed_orders = self.order_executor.process_signals(self.options_signals)
        
        if executed_orders:
            logger.info(f"Executed {len(executed_orders)} orders")
            self.executed_orders.update(executed_orders)
        
        # Check for exit conditions on existing positions
        platform_positions = self.order_executor.get_positions()
        
        for position in platform_positions:
            symbol = position.get('symbol')
            
            # Skip if no signal for this symbol
            if symbol not in self.options_signals:
                continue
            
            signal = self.options_signals[symbol]
            
            # Check for exit conditions
            exit_needed = False
            
            # Check for signal reversal
            if position.get('asset_type') == 'option':
                option_type = position.get('option_type')
                position_type = position.get('position_type')
                
                if option_type == 'call' and position_type == 'long' and signal['signal'] == 'BEARISH':
                    exit_needed = True
                    logger.info(f"Signal reversal for {symbol}: BULLISH to BEARISH")
                    
                elif option_type == 'put' and position_type == 'long' and signal['signal'] == 'BULLISH':
                    exit_needed = True
                    logger.info(f"Signal reversal for {symbol}: BEARISH to BULLISH")
            
            # Close position if needed
            if exit_needed:
                logger.info(f"Closing position for {symbol} due to signal reversal")
                self.order_executor.close_position(position)
    
    def _save_state(self):
        """Save current state to output directory"""
        try:
            # Get account info
            account_info = self.order_executor.get_account_info()
            
            # Save account info
            account_file = os.path.join(self.output_dir, "account_info.json")
            with open(account_file, 'w') as f:
                json.dump(account_info, f, indent=4)
            
            # Get positions
            positions = self.order_executor.get_positions()
            
            # Save positions
            positions_file = os.path.join(self.output_dir, "positions.json")
            with open(positions_file, 'w') as f:
                json.dump(positions, f, indent=4)
            
            # Save signals
            signals_file = os.path.join(self.output_dir, "signals.json")
            with open(signals_file, 'w') as f:
                # Convert DataFrame objects to dictionaries
                signals_copy = {}
                for symbol, signal in self.options_signals.items():
                    signal_copy = {}
                    for key, value in signal.items():
                        if isinstance(value, pd.DataFrame):
                            signal_copy[key] = "DataFrame"
                        else:
                            signal_copy[key] = value
                    signals_copy[symbol] = signal_copy
                
                json.dump(signals_copy, f, indent=4)
            
            # Save real-time data
            real_time_file = os.path.join(self.output_dir, "real_time_data.json")
            with open(real_time_file, 'w') as f:
                # Convert datetime objects to strings
                real_time_copy = {}
                for symbol, data in self.real_time_data.items():
                    data_copy = data.copy()
                    if 'timestamp' in data_copy and isinstance(data_copy['timestamp'], datetime):
                        data_copy['timestamp'] = data_copy['timestamp'].isoformat()
                    real_time_copy[symbol] = data_copy
                
                json.dump(real_time_copy, f, indent=4)
            
            logger.info("Saved current state to output directory")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def run(self):
        """Run the live trading bot"""
        logger.info("Starting live trading bot")
        
        try:
            # Initialize the bot
            self.initialize()
            
            # Run the update loop
            self.data_provider.run_update_loop(
                self.symbols,
                callback=self.process_data_update
            )
        except KeyboardInterrupt:
            logger.info("Live trading bot stopped by user")
        except Exception as e:
            logger.error(f"Error in live trading bot: {e}")
        finally:
            # Save final state
            self._save_state()
            
            # Save data
            self.data_provider.save_data(self.output_dir)
            
            logger.info("Live trading bot shutdown complete")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Live Trading Bot')
    
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
                        help='List of stock symbols to trade')
    parser.add_argument('--config', default=None,
                        help='Path to strategy configuration JSON file')
    parser.add_argument('--stock-provider', default='finnhub', choices=['finnhub', 'yahoo', 'polygon'],
                        help='Stock data provider to use')
    parser.add_argument('--options-provider', default='polygon', choices=['yahoo', 'polygon'],
                        help='Options data provider to use')
    parser.add_argument('--stock-api-key', default=None,
                        help='API key for the stock data provider')
    parser.add_argument('--options-api-key', default=None,
                        help='API key for the options data provider')
    parser.add_argument('--interval', type=int, default=60,
                        help='Update interval in seconds')
    parser.add_argument('--output-dir', default=OUTPUT_DIR,
                        help='Directory to save output files')
    parser.add_argument('--platform', default='paper', choices=['investopedia', 'paper'],
                        help='Trading platform to use')
    parser.add_argument('--auth-token', default=None,
                        help='Authentication bearer token for Investopedia')
    parser.add_argument('--username', default=None,
                        help='Username for the trading platform (legacy)')
    parser.add_argument('--password', default=None,
                        help='Password for the trading platform (legacy)')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create and run the live trading bot
    bot = LiveTradingBot(
        args.symbols,
        config_path=args.config,
        stock_provider=args.stock_provider,
        options_provider=args.options_provider,
        stock_api_key=args.stock_api_key,
        options_api_key=args.options_api_key,
        update_interval=args.interval,
        output_dir=args.output_dir,
        trading_platform=args.platform,
        username=args.username,
        password=args.password,
        auth_token=args.auth_token
    )
    
    bot.run()
