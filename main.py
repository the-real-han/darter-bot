#!/usr/bin/env python3
"""
Main Module for Trading Bot
-------------------------
Entry point for the trading bot application
"""

import os
import sys
import logging
import argparse
import pandas as pd
import yfinance as yf
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_handler import DataHandler
from strategy import Strategy
from trader import Trader
from backtest import Backtest
from visualization import Visualizer
from options_handler import OptionsHandler

# Create output directory for generated files
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure logging
log_file = os.path.join(OUTPUT_DIR, "trading_bot.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('trading_bot')

class TradingBot:
    def __init__(self, symbols, timeframe='1d', period='3mo', output_dir=OUTPUT_DIR):
        """
        Initialize the trading bot with symbols to trade.
        
        Args:
            symbols (list): List of stock symbols to analyze and trade
            timeframe (str): Data timeframe (e.g., '1d', '1h', '15m')
            period (str): Historical data period (e.g., '1d', '5d', '1mo', '3mo', '1y')
            output_dir (str): Directory to save output files
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.period = period
        self.output_dir = output_dir
        
        # Initialize components
        self.data_handler = DataHandler(timeframe=timeframe, period=period)
        self.strategy = Strategy()
        self.trader = Trader(symbols)
        self.backtest = Backtest()
        self.visualizer = Visualizer()
        self.options_handler = OptionsHandler()
        
        # Data containers
        self.data = {}
        self.signals = {}
        self.backtest_results = {}
    
    def run(self, mode='backtest', include_options=False):
        """
        Run the trading bot
        
        Args:
            mode (str): 'backtest' for backtesting, 'live' for live trading
            include_options (bool): Whether to include options trading
            
        Returns:
            dict: Results of the operation
        """
        logger.info(f"Starting trading bot in {mode} mode")
        
        # Fetch market data
        self.data = self.data_handler.fetch_data(self.symbols)
        
        # Calculate technical indicators
        for symbol in self.symbols:
            if symbol in self.data:
                self.data[symbol] = self.data_handler.calculate_indicators(symbol)
        
        # Generate trading signals
        self.signals = self.strategy.generate_signals(self.data)
        
        # Handle options if requested
        if include_options:
            self.options_signals = {}
            for symbol in self.symbols:
                if symbol in self.signals:
                    current_signal = self.signals[symbol]['Signal'].iloc[-1]
                    current_price = self.signals[symbol]['Close'].iloc[-1]
                    
                    options_signal = self.options_handler.options_strategy_signals(
                        symbol, current_signal, current_price
                    )
                    
                    if options_signal:
                        self.options_signals[symbol] = options_signal
                        logger.info(f"Generated options signal for {symbol}: {options_signal['strategy']}")
        
        if mode == 'backtest':
            # Run backtest
            self.backtest_results = self.backtest.run(self.signals)
            
            # Generate backtest report
            report = self.backtest.generate_report(self.backtest_results)
            print("\nBacktest Results:")
            print(report)
            
            # Save report to CSV
            report_path = os.path.join(self.output_dir, "backtest_report.csv")
            report.to_csv(report_path)
            logger.info(f"Saved backtest report to {report_path}")
            
            # Visualize results for the first symbol
            if self.symbols:
                self.backtest.visualize(self.symbols[0], self.backtest_results, self.output_dir)
                
            return self.backtest_results
            
        elif mode == 'live':
            # Execute trades based on signals
            positions = self.trader.execute_trades(self.signals)
            
            return positions
    
    def visualize_all(self):
        """Visualize technical analysis for all symbols"""
        for symbol in self.symbols:
            if symbol in self.signals:
                self.visualizer.plot_technical_analysis(
                    self.signals[symbol], 
                    symbol, 
                    save_path=os.path.join(self.output_dir, f"{symbol}_analysis.png")
                )
        
        # Plot portfolio performance if backtest results are available
        if self.backtest_results:
            self.visualizer.plot_portfolio_performance(
                self.backtest_results,
                save_path=os.path.join(self.output_dir, "portfolio_performance.png")
            )
    
    def fetch_benchmark_data(self, benchmark_symbol='^GSPC'):
        """
        Fetch benchmark data for comparison
        
        Args:
            benchmark_symbol (str): Symbol for benchmark (default: S&P 500)
            
        Returns:
            DataFrame: Benchmark data
        """
        try:
            ticker = yf.Ticker(benchmark_symbol)
            benchmark_data = ticker.history(period=self.period, interval=self.timeframe)
            logger.info(f"Fetched benchmark data for {benchmark_symbol}")
            return benchmark_data
        except Exception as e:
            logger.error(f"Error fetching benchmark data: {e}")
            return None
    
    def compare_to_benchmark(self):
        """Compare strategy performance to benchmark"""
        benchmark_data = self.fetch_benchmark_data()
        
        if benchmark_data is not None and self.backtest_results:
            self.visualizer.plot_comparison_chart(
                self.backtest_results,
                benchmark_data,
                save_path=os.path.join(self.output_dir, "benchmark_comparison.png")
            )


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Trading Bot')
    
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
                        help='List of stock symbols to trade')
    parser.add_argument('--mode', choices=['backtest', 'live'], default='backtest',
                        help='Trading mode: backtest or live')
    parser.add_argument('--timeframe', default='1d',
                        help='Data timeframe (e.g., 1d, 1h, 15m)')
    parser.add_argument('--period', default='3mo',
                        help='Historical data period (e.g., 1d, 5d, 1mo, 3mo, 1y)')
    parser.add_argument('--options', action='store_true',
                        help='Include options trading')
    parser.add_argument('--output-dir', default=OUTPUT_DIR,
                        help='Directory to save output files')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create and run the trading bot
    bot = TradingBot(args.symbols, args.timeframe, args.period, args.output_dir)
    results = bot.run(mode=args.mode, include_options=args.options)
    
    # Visualize results
    bot.visualize_all()
    
    # Compare to benchmark
    if args.mode == 'backtest':
        bot.compare_to_benchmark()
