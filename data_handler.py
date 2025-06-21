#!/usr/bin/env python3
"""
Data Handler Module for Trading Bot
----------------------------------
Handles data fetching and processing for technical analysis
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging

logger = logging.getLogger('trading_bot.data')

class DataHandler:
    def __init__(self, timeframe='1d', period='3mo'):
        """
        Initialize the data handler
        
        Args:
            timeframe (str): Data timeframe (e.g., '1d', '1h', '15m')
            period (str): Historical data period (e.g., '1d', '5d', '1mo', '3mo', '1y')
        """
        self.timeframe = timeframe
        self.period = period
        self.data = {}
    
    def fetch_data(self, symbols):
        """
        Fetch historical market data for all symbols
        
        Args:
            symbols (list): List of stock symbols to fetch data for
            
        Returns:
            dict: Dictionary of DataFrames with historical data for each symbol
        """
        logger.info(f"Fetching data for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                self.data[symbol] = ticker.history(period=self.period, interval=self.timeframe)
                logger.info(f"Fetched {len(self.data[symbol])} data points for {symbol}")
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
        
        return self.data
    
    def calculate_indicators(self, symbol):
        """
        Calculate technical indicators for a given symbol
        
        Args:
            symbol (str): The stock symbol to calculate indicators for
            
        Returns:
            DataFrame: DataFrame with added technical indicators
        """
        if symbol not in self.data or self.data[symbol].empty:
            logger.error(f"No data available for {symbol}")
            return None
            
        df = self.data[symbol].copy()
        
        # Calculate Simple Moving Averages
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        
        # Calculate Exponential Moving Averages
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        
        # Calculate MACD
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # Calculate RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Calculate Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + 2 * df['BB_Std']
        df['BB_Lower'] = df['BB_Middle'] - 2 * df['BB_Std']
        
        # Calculate Average True Range (ATR)
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = true_range.rolling(window=14).mean()
        
        return df
