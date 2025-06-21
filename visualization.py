#!/usr/bin/env python3
"""
Visualization Module for Trading Bot
----------------------------------
Implements visualization tools for technical analysis and backtest results
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger('trading_bot.visualization')

class Visualizer:
    def __init__(self):
        """Initialize the visualizer"""
        pass
    
    def plot_technical_analysis(self, df, symbol, save_path=None):
        """
        Create a technical analysis chart for a symbol
        
        Args:
            df (DataFrame): DataFrame with price data and indicators
            symbol (str): Symbol to visualize
            save_path (str): Path to save the chart (if None, display only)
        """
        # Create a figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 16), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Plot price and moving averages
        ax1.plot(df.index, df['Close'], label='Close Price')
        ax1.plot(df.index, df['SMA20'], label='SMA20')
        ax1.plot(df.index, df['SMA50'], label='SMA50')
        ax1.plot(df.index, df['BB_Upper'], 'r--', label='BB Upper')
        ax1.plot(df.index, df['BB_Lower'], 'g--', label='BB Lower')
        
        # Plot buy/sell signals if available
        if 'Signal' in df.columns:
            buy_signals = df[df['Signal'] == 1]
            sell_signals = df[df['Signal'] == -1]
            
            ax1.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='g', s=100, label='Buy Signal')
            ax1.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='r', s=100, label='Sell Signal')
        
        ax1.set_title(f'{symbol} Price and Indicators')
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
        
        # Plot MACD
        ax3.plot(df.index, df['MACD'], label='MACD')
        ax3.plot(df.index, df['MACD_Signal'], label='Signal Line')
        ax3.bar(df.index, df['MACD_Hist'], label='Histogram')
        ax3.set_ylabel('MACD')
        ax3.legend()
        ax3.grid(True)
        
        plt.tight_layout()
        
        if save_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            plt.savefig(save_path)
            logger.info(f"Saved technical analysis chart for {symbol} to {save_path}")
            plt.close(fig)
        else:
            plt.show()
    
    def plot_portfolio_performance(self, results, save_path=None):
        """
        Plot portfolio performance from backtest results
        
        Args:
            results (dict): Dictionary of backtest results
            save_path (str): Path to save the chart (if None, display only)
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for symbol, metrics in results.items():
            if 'Data' in metrics and 'Portfolio' in metrics['Data'].columns:
                df = metrics['Data']
                # Normalize to percentage return
                normalized = df['Portfolio'] / df['Portfolio'].iloc[0] * 100
                ax.plot(df.index, normalized, label=f"{symbol} ({metrics['Total_Return']:.1f}%)")
        
        ax.set_title('Portfolio Performance')
        ax.set_ylabel('Return (%)')
        ax.legend()
        ax.grid(True)
        
        if save_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            plt.savefig(save_path)
            logger.info(f"Saved portfolio performance chart to {save_path}")
            plt.close(fig)
        else:
            plt.show()
    
    def plot_comparison_chart(self, results, benchmark_data=None, save_path=None):
        """
        Plot comparison chart between strategy and benchmark
        
        Args:
            results (dict): Dictionary of backtest results
            benchmark_data (DataFrame): Benchmark data (e.g., S&P 500)
            save_path (str): Path to save the chart (if None, display only)
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot strategy performance
        for symbol, metrics in results.items():
            if 'Data' in metrics and 'Portfolio' in metrics['Data'].columns:
                df = metrics['Data']
                # Normalize to percentage return
                normalized = df['Portfolio'] / df['Portfolio'].iloc[0] * 100
                ax.plot(df.index, normalized, label=f"{symbol} Strategy ({metrics['Total_Return']:.1f}%)")
        
        # Plot benchmark if provided
        if benchmark_data is not None and not benchmark_data.empty:
            normalized_benchmark = benchmark_data['Close'] / benchmark_data['Close'].iloc[0] * 100
            ax.plot(benchmark_data.index, normalized_benchmark, 'k--', label='Benchmark')
        
        ax.set_title('Strategy vs Benchmark')
        ax.set_ylabel('Return (%)')
        ax.legend()
        ax.grid(True)
        
        if save_path:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            plt.savefig(save_path)
            logger.info(f"Saved comparison chart to {save_path}")
            plt.close(fig)
        else:
            plt.show()
