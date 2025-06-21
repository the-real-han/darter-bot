#!/usr/bin/env python3
"""
Backtest Module for Trading Bot
-----------------------------
Implements backtesting functionality for trading strategies
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger('trading_bot.backtest')

class Backtest:
    def __init__(self):
        """Initialize the backtest handler"""
        pass
    
    def run(self, signals, initial_capital=100000):
        """
        Run backtest on the trading signals
        
        Args:
            signals (dict): Dictionary of DataFrames with signal columns
            initial_capital (float): Initial capital for backtesting
            
        Returns:
            dict: Dictionary of performance metrics for each symbol
        """
        results = {}
        
        for symbol, df in signals.items():
            if df is None or df.empty or 'Signal' not in df.columns:
                continue
                
            df_copy = df.copy()
            
            # Initialize portfolio columns
            df_copy['Position'] = 0
            df_copy['Cash'] = initial_capital
            df_copy['Holdings'] = 0
            df_copy['Portfolio'] = initial_capital
            
            position = 0
            entry_price = 0
            
            for i in range(1, len(df_copy)):
                # Update position based on previous day's signal
                if df_copy['Signal'].iloc[i-1] == 1 and position == 0:  # Buy signal
                    position = initial_capital / df_copy['Close'].iloc[i]
                    entry_price = df_copy['Close'].iloc[i]
                    df_copy.loc[df_copy.index[i], 'Cash'] = 0
                    df_copy.loc[df_copy.index[i], 'Holdings'] = position * df_copy['Close'].iloc[i]
                    
                elif df_copy['Signal'].iloc[i-1] == -1 and position > 0:  # Sell signal
                    df_copy.loc[df_copy.index[i], 'Cash'] = position * df_copy['Close'].iloc[i]
                    df_copy.loc[df_copy.index[i], 'Holdings'] = 0
                    position = 0
                    
                else:  # Hold position
                    df_copy.loc[df_copy.index[i], 'Cash'] = df_copy['Cash'].iloc[i-1]
                    df_copy.loc[df_copy.index[i], 'Holdings'] = position * df_copy['Close'].iloc[i]
                
                df_copy.loc[df_copy.index[i], 'Position'] = position
                df_copy.loc[df_copy.index[i], 'Portfolio'] = df_copy['Cash'].iloc[i] + df_copy['Holdings'].iloc[i]
            
            # Calculate performance metrics
            df_copy['Returns'] = df_copy['Portfolio'].pct_change()
            
            results[symbol] = {
                'Final_Portfolio': df_copy['Portfolio'].iloc[-1],
                'Total_Return': (df_copy['Portfolio'].iloc[-1] / initial_capital - 1) * 100,
                'Max_Drawdown': (df_copy['Portfolio'] / df_copy['Portfolio'].cummax() - 1).min() * 100,
                'Sharpe_Ratio': df_copy['Returns'].mean() / df_copy['Returns'].std() * (252 ** 0.5) if df_copy['Returns'].std() != 0 else 0,
                'Data': df_copy  # Store the DataFrame for further analysis
            }
            
            logger.info(f"Backtest results for {symbol}: Total Return: {results[symbol]['Total_Return']:.2f}%, Max Drawdown: {results[symbol]['Max_Drawdown']:.2f}%")
        
        return results
    
    def visualize(self, symbol, results, output_dir=None):
        """
        Visualize backtest results for a symbol
        
        Args:
            symbol (str): Symbol to visualize
            results (dict): Dictionary of backtest results
            output_dir (str): Directory to save output files
        """
        if symbol not in results:
            logger.error(f"No backtest results available for {symbol}")
            return
            
        df = results[symbol]['Data']
        
        # Create a figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 16), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Plot price and moving averages
        ax1.plot(df.index, df['Close'], label='Close Price')
        ax1.plot(df.index, df['SMA20'], label='SMA20')
        ax1.plot(df.index, df['SMA50'], label='SMA50')
        ax1.plot(df.index, df['BB_Upper'], 'r--', label='BB Upper')
        ax1.plot(df.index, df['BB_Lower'], 'g--', label='BB Lower')
        
        # Plot buy/sell signals
        buy_signals = df[df['Signal'] == 1]
        sell_signals = df[df['Signal'] == -1]
        
        ax1.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='g', s=100, label='Buy Signal')
        ax1.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='r', s=100, label='Sell Signal')
        
        ax1.set_title(f'{symbol} Price and Signals')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot RSI
        ax2.plot(df.index, df['RSI'], label='RSI')
        ax2.axhline(y=70, color='r', linestyle='--', label='Overbought')
        ax2.axhline(y=30, color='g', linestyle='--', label='Oversold')
        ax2.set_ylabel('RSI')
        ax2.legend()
        ax2.grid(True)
        
        # Plot portfolio value
        ax3.plot(df.index, df['Portfolio'], label='Portfolio Value')
        ax3.set_ylabel('Portfolio Value')
        ax3.legend()
        ax3.grid(True)
        
        plt.tight_layout()
        
        # Save the figure
        if output_dir:
            save_path = os.path.join(output_dir, f'{symbol}_backtest.png')
        else:
            save_path = f'{symbol}_backtest.png'
            
        plt.savefig(save_path)
        logger.info(f"Saved backtest visualization for {symbol} to {save_path}")
        plt.close(fig)
    
    def generate_report(self, results):
        """
        Generate a summary report of backtest results
        
        Args:
            results (dict): Dictionary of backtest results
            
        Returns:
            DataFrame: Summary of backtest results
        """
        summary = {}
        
        for symbol, metrics in results.items():
            summary[symbol] = {
                'Total Return (%)': metrics['Total_Return'],
                'Max Drawdown (%)': metrics['Max_Drawdown'],
                'Sharpe Ratio': metrics['Sharpe_Ratio'],
                'Final Portfolio Value': metrics['Final_Portfolio']
            }
        
        return pd.DataFrame.from_dict(summary, orient='index')
