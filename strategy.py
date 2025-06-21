#!/usr/bin/env python3
"""
Strategy Module for Trading Bot
------------------------------
Implements various technical analysis strategies
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger('trading_bot.strategy')

class Strategy:
    def __init__(self):
        """Initialize the strategy handler"""
        self.signals = {}
    
    def generate_signals(self, data_dict):
        """
        Generate trading signals for all symbols based on technical analysis
        
        Args:
            data_dict (dict): Dictionary of DataFrames with technical indicators
            
        Returns:
            dict: Dictionary of DataFrames with added signal columns
        """
        for symbol, df in data_dict.items():
            try:
                if df is None or df.empty:
                    continue
                
                # Initialize signal column
                df['Signal'] = 0  # 0: no signal, 1: buy, -1: sell
                
                # Strategy 1: Moving Average Crossover
                df.loc[df['SMA20'] > df['SMA50'], 'MA_Signal'] = 1
                df.loc[df['SMA20'] < df['SMA50'], 'MA_Signal'] = -1
                
                # Strategy 2: RSI Overbought/Oversold
                df.loc[df['RSI'] < 30, 'RSI_Signal'] = 1
                df.loc[df['RSI'] > 70, 'RSI_Signal'] = -1
                
                # Strategy 3: MACD Crossover
                df.loc[df['MACD'] > df['MACD_Signal'], 'MACD_Signal'] = 1
                df.loc[df['MACD'] < df['MACD_Signal'], 'MACD_Signal'] = -1
                
                # Strategy 4: Bollinger Band Breakouts
                df.loc[df['Close'] < df['BB_Lower'], 'BB_Signal'] = 1
                df.loc[df['Close'] > df['BB_Upper'], 'BB_Signal'] = -1
                
                # Combine signals (simple approach - can be customized)
                # Here we're just taking the sum of all signals
                df['Signal'] = df['MA_Signal'].fillna(0) + df['RSI_Signal'].fillna(0) + \
                               df['MACD_Signal'].fillna(0) + df['BB_Signal'].fillna(0)
                
                # Normalize signals: positive = buy, negative = sell
                df.loc[df['Signal'] > 0, 'Signal'] = 1
                df.loc[df['Signal'] < 0, 'Signal'] = -1
                
                self.signals[symbol] = df
                logger.info(f"Generated signals for {symbol}")
                
            except Exception as e:
                logger.error(f"Error generating signals for {symbol}: {e}")
        
        return self.signals
    
    def custom_strategy(self, df):
        """
        Template for implementing a custom trading strategy
        
        Args:
            df (DataFrame): DataFrame with price data and indicators
            
        Returns:
            DataFrame: DataFrame with added signal column
        """
        # Initialize signal column
        df['Custom_Signal'] = 0
        
        # Implement your custom strategy logic here
        # Example: Buy when RSI crosses above 30 and MACD is positive
        buy_condition = (df['RSI'] > 30) & (df['RSI'].shift(1) <= 30) & (df['MACD'] > 0)
        df.loc[buy_condition, 'Custom_Signal'] = 1
        
        # Example: Sell when RSI crosses below 70 or MACD crosses below signal line
        sell_condition = (df['RSI'] < 70) & (df['RSI'].shift(1) >= 70) | \
                         (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))
        df.loc[sell_condition, 'Custom_Signal'] = -1
        
        return df
