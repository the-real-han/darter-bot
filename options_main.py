#!/usr/bin/env python3
"""
Options Trading Bot Main Module
-----------------------------
Entry point for the options trading bot application
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
from options_handler import OptionsHandler
from options_strategy import OptionsStrategy
from options_backtest import OptionsBacktest
from visualization import Visualizer
from strategy_config import load_strategy_config, save_strategy_config, extract_current_strategy

# Create output directory for generated files
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure logging
log_file = os.path.join(OUTPUT_DIR, "options_trading_bot.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('options_trading_bot')

class OptionsTradingBot:
    def __init__(self, symbols, timeframe='1d', period='3mo', output_dir=OUTPUT_DIR, config_path=None):
        """
        Initialize the options trading bot with symbols to trade.
        
        Args:
            symbols (list): List of stock symbols to analyze and trade options on
            timeframe (str): Data timeframe (e.g., '1d', '1h', '15m')
            period (str): Historical data period (e.g., '1d', '5d', '1mo', '3mo', '1y')
            output_dir (str): Directory to save output files
            config_path (str): Path to the strategy configuration file
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.period = period
        self.output_dir = output_dir
        self.config_path = config_path
        
        # Load strategy configuration
        self.config = load_strategy_config(config_path)
        
        # Initialize components
        self.data_handler = DataHandler(timeframe=timeframe, period=period)
        self.options_handler = OptionsHandler()
        self.options_strategy = OptionsStrategy(config_path)
        self.options_backtest = OptionsBacktest()
        self.visualizer = Visualizer()
        
        # Data containers
        self.data = {}
        self.options_data = {}
        self.options_signals = {}
        self.backtest_results = {}
        
        logger.info(f"Options trading bot initialized with configuration from {config_path if config_path else 'default'}")
    
    def run(self, mode='backtest', save_default_strategy=False):
        """
        Run the options trading bot
        
        Args:
            mode (str): 'backtest' for backtesting, 'live' for live trading
            save_default_strategy (bool): Whether to save the current strategy to default.json
            
        Returns:
            dict: Results of the operation
        """
        logger.info(f"Starting options trading bot in {mode} mode")
        
        # Fetch market data for underlying stocks
        self.data = self.data_handler.fetch_data(self.symbols)
        
        # Calculate technical indicators
        for symbol in self.symbols:
            if symbol in self.data:
                self.data[symbol] = self.data_handler.calculate_indicators(symbol)
        
        # Fetch options data
        for symbol in self.symbols:
            self.options_data[symbol] = self.options_handler.fetch_options_chain(symbol)
            
            if self.options_data[symbol]:
                logger.info(f"Fetched options data for {symbol} with expiry {self.options_data[symbol]['expiry']}")
            else:
                logger.warning(f"Could not fetch options data for {symbol}")
        
        # Generate options trading signals
        self.options_signals = self.options_strategy.generate_signals(self.data, self.options_data)
        
        # Save current strategy to default.json if requested
        if save_default_strategy:
            current_strategy = extract_current_strategy(self.config)
            default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'default_strategy.json')
            save_strategy_config(current_strategy, default_path)
            logger.info(f"Saved current strategy configuration to {default_path}")
        
        # Print options signals
        for symbol, signal in self.options_signals.items():
            logger.info(f"Options signal for {symbol}: {signal['strategy']}")
            
            # Calculate expected profit metrics
            profit_metrics = self.options_strategy.calculate_expected_profit(signal)
            if profit_metrics:
                for metric, value in profit_metrics.items():
                    logger.info(f"  {metric}: {value}")
        
        if mode == 'backtest':
            # Run options backtest with configuration
            self.backtest_results = self.options_backtest.run(
                self.data, 
                self.options_signals,
                config=self.config
            )
            
            # Generate backtest report
            report = self.options_backtest.generate_report(self.backtest_results)
            print("\nOptions Backtest Results:")
            print(report)
            
            # Save report to CSV
            report_path = os.path.join(self.output_dir, "options_backtest_report.csv")
            report.to_csv(report_path)
            logger.info(f"Saved options backtest report to {report_path}")
            
            # Save exit reasons report
            exit_reasons = {}
            for symbol, result in self.backtest_results.items():
                if 'Exit_Reasons' in result:
                    exit_reasons[symbol] = result['Exit_Reasons']
            
            if exit_reasons:
                exit_report = pd.DataFrame.from_dict(exit_reasons, orient='index')
                exit_report_path = os.path.join(self.output_dir, "exit_reasons_report.csv")
                exit_report.to_csv(exit_report_path)
                logger.info(f"Saved exit reasons report to {exit_report_path}")
            
            # Visualize results for each symbol
            for symbol in self.symbols:
                if symbol in self.backtest_results:
                    self.options_backtest.visualize(symbol, self.backtest_results, self.output_dir)
            
            # Plot portfolio performance
            self.visualize_portfolio_performance()
            
            return self.backtest_results
            
        elif mode == 'live':
            # In live mode, just return the generated signals
            return self.options_signals
    
    def visualize_portfolio_performance(self):
        """Visualize portfolio performance from backtest results"""
        if not self.backtest_results:
            return
            
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for symbol, metrics in self.backtest_results.items():
            if 'Data' in metrics and 'Portfolio' in metrics['Data'].columns:
                df = metrics['Data']
                # Normalize to percentage return
                normalized = df['Portfolio'] / df['Portfolio'].iloc[0] * 100
                ax.plot(df.index, normalized, label=f"{symbol} ({metrics['Strategy']}: {metrics['Total_Return']:.1f}%)")
        
        ax.set_title('Options Strategies Performance')
        ax.set_ylabel('Return (%)')
        ax.legend()
        ax.grid(True)
        
        save_path = os.path.join(self.output_dir, "options_portfolio_performance.png")
        plt.savefig(save_path)
        logger.info(f"Saved options portfolio performance chart to {save_path}")
        plt.close(fig)
    
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


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Options Trading Bot')
    
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
                        help='List of stock symbols to trade options on')
    parser.add_argument('--mode', choices=['backtest', 'live'], default='backtest',
                        help='Trading mode: backtest or live')
    parser.add_argument('--timeframe', default='1d',
                        help='Data timeframe (e.g., 1d, 1h, 15m)')
    parser.add_argument('--period', default='3mo',
                        help='Historical data period (e.g., 1d, 5d, 1mo, 3mo, 1y)')
    parser.add_argument('--output-dir', default=OUTPUT_DIR,
                        help='Directory to save output files')
    parser.add_argument('--config', default=None,
                        help='Path to strategy configuration JSON file')
    parser.add_argument('--save-default', action='store_true',
                        help='Save current strategy to default_strategy.json')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create and run the options trading bot
    bot = OptionsTradingBot(
        args.symbols, 
        args.timeframe, 
        args.period, 
        args.output_dir,
        args.config
    )
    results = bot.run(mode=args.mode, save_default_strategy=args.save_default)
