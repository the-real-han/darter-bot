#!/usr/bin/env python3
"""
Yahoo Finance Data Provider Module
-------------------------------
Implements the Yahoo Finance market data provider
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
from .base_provider import BaseDataProvider

logger = logging.getLogger('trading_bot.data_providers.yahoo')

class YahooDataProvider(BaseDataProvider):
    """Yahoo Finance market data provider implementation"""
    
    def initialize_client(self, **kwargs):
        """Initialize the Yahoo Finance client (not needed for yfinance)"""
        self.client = True  # Just a placeholder since yfinance doesn't need a client
        logger.info("Yahoo Finance provider initialized")
    
    def get_historical_data(self, symbol, period='3mo', interval='1d'):
        """
        Get historical market data for a symbol
        
        Args:
            symbol (str): Stock symbol
            period (str): Time period (e.g., '1d', '5d', '1mo', '3mo', '1y')
            interval (str): Data interval (e.g., '1m', '5m', '15m', '1h', '1d')
            
        Returns:
            DataFrame: Historical market data
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            logger.info(f"Fetched {len(df)} historical data points for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_real_time_data(self, symbol):
        """
        Get real-time market data for a symbol
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Real-time market data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get the most recent data (1m interval)
            recent_data = ticker.history(period='1d', interval='1m')
            
            if recent_data.empty:
                logger.warning(f"No recent data available for {symbol}")
                return {}
            
            # Get the last row
            last_data = recent_data.iloc[-1]
            
            # Format as a quote dictionary
            quote = {
                'c': last_data['Close'],  # Current price
                'h': last_data['High'],   # High price of the day
                'l': last_data['Low'],    # Low price of the day
                'o': last_data['Open'],   # Open price of the day
                'pc': recent_data['Close'].iloc[0],  # Previous close
                'timestamp': last_data.name  # Timestamp
            }
            
            logger.info(f"Fetched real-time data for {symbol}")
            return quote
            
        except Exception as e:
            logger.error(f"Error fetching real-time data for {symbol}: {e}")
            return {}
    
    def get_options_chain(self, symbol):
        """
        Get options chain data for a symbol
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Options chain data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates
            expirations = ticker.options
            
            if not expirations:
                logger.warning(f"No options available for {symbol}")
                return {}
            
            # Get options for the first expiration date
            expiry = expirations[0]
            
            # Fetch options chain
            options = ticker.option_chain(expiry)
            
            # Get current stock price
            current_price = ticker.history(period='1d')['Close'].iloc[-1]
            
            options_data = {
                'symbol': symbol,
                'current_price': current_price,
                'expiry': expiry,
                'calls': options.calls,
                'puts': options.puts
            }
            
            logger.info(f"Fetched options chain for {symbol} with expiry {expiry}")
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol}: {e}")
            return {}
