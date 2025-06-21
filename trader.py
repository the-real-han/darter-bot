#!/usr/bin/env python3
"""
Trader Module for Trading Bot
----------------------------
Handles trade execution and position management
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger('trading_bot.trader')

class Trader:
    def __init__(self, symbols):
        """
        Initialize the trader
        
        Args:
            symbols (list): List of stock symbols to trade
        """
        self.symbols = symbols
        self.positions = {}
        
        # Initialize positions dictionary
        for symbol in symbols:
            self.positions[symbol] = 0
    
    def execute_trades(self, signals, capital_per_trade=10000, max_positions=5):
        """
        Execute trades based on generated signals
        
        Args:
            signals (dict): Dictionary of DataFrames with signal columns
            capital_per_trade (float): Amount of capital to allocate per trade
            max_positions (int): Maximum number of open positions allowed
            
        Returns:
            dict: Updated positions dictionary
        """
        current_positions = sum(1 for pos in self.positions.values() if pos != 0)
        
        for symbol in self.symbols:
            if symbol not in signals or signals[symbol] is None:
                continue
                
            df = signals[symbol]
            if df.empty:
                continue
                
            current_signal = df['Signal'].iloc[-1]
            current_price = df['Close'].iloc[-1]
            
            # Check if we should buy
            if current_signal > 0 and self.positions[symbol] == 0 and current_positions < max_positions:
                # Calculate position size
                position_size = int(capital_per_trade / current_price)
                self.positions[symbol] = position_size
                current_positions += 1
                
                logger.info(f"BUY: {position_size} shares of {symbol} at ${current_price:.2f}")
                
            # Check if we should sell
            elif current_signal < 0 and self.positions[symbol] > 0:
                position_size = self.positions[symbol]
                self.positions[symbol] = 0
                current_positions -= 1
                
                logger.info(f"SELL: {position_size} shares of {symbol} at ${current_price:.2f}")
        
        return self.positions
    
    def calculate_position_size(self, symbol, price, risk_per_trade=0.01, stop_loss_pct=0.02, capital=100000):
        """
        Calculate position size based on risk management rules
        
        Args:
            symbol (str): Symbol to trade
            price (float): Current price
            risk_per_trade (float): Percentage of capital to risk per trade
            stop_loss_pct (float): Stop loss percentage
            capital (float): Total capital
            
        Returns:
            int: Number of shares to trade
        """
        # Calculate dollar risk amount
        risk_amount = capital * risk_per_trade
        
        # Calculate stop loss price
        stop_loss = price * (1 - stop_loss_pct)
        
        # Calculate position size
        position_size = risk_amount / (price - stop_loss)
        
        return int(position_size)
    
    def get_portfolio_value(self, prices):
        """
        Calculate current portfolio value
        
        Args:
            prices (dict): Dictionary of current prices for each symbol
            
        Returns:
            float: Total portfolio value
        """
        portfolio_value = 0
        
        for symbol, position in self.positions.items():
            if position > 0 and symbol in prices:
                portfolio_value += position * prices[symbol]
        
        return portfolio_value
