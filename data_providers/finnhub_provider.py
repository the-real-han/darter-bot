#!/usr/bin/env python3
"""
Finnhub Data Provider Module
--------------------------
Implements the Finnhub market data provider
"""

import finnhub
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from .base_provider import BaseDataProvider

logger = logging.getLogger('trading_bot.data_providers.finnhub')

class FinnhubDataProvider(BaseDataProvider):
    """Finnhub market data provider implementation"""
    
    def initialize_client(self, **kwargs):
        """Initialize the Finnhub API client"""
        try:
            self.client = finnhub.Client(api_key=self.api_key)
            logger.info("Finnhub client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Finnhub client: {e}")
            self.client = None
    
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
        if self.client is None:
            logger.error("Finnhub client not initialized")
            return pd.DataFrame()
        
        try:
            # Convert period to days and calculate start date
            days = self.convert_period_to_days(period)
            end_date = int(time.time())
            start_date = end_date - (days * 24 * 60 * 60)
            
            # Convert interval to Finnhub resolution
            resolution = self._convert_interval_to_resolution(interval)
            
            # Fetch data from Finnhub
            data = self.client.stock_candles(symbol, resolution, start_date, end_date)
            
            if data['s'] == 'no_data':
                logger.warning(f"No data available for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame({
                'Open': data['o'],
                'High': data['h'],
                'Low': data['l'],
                'Close': data['c'],
                'Volume': data['v']
            }, index=pd.to_datetime([datetime.fromtimestamp(ts) for ts in data['t']]))
            
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
        if self.client is None:
            logger.error("Finnhub client not initialized")
            return {}
        
        try:
            # Get real-time quote
            quote = self.client.quote(symbol)
            
            # Add timestamp
            quote['timestamp'] = datetime.now()
            
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
        if self.client is None:
            logger.error("Finnhub client not initialized")
            return {}
        
        try:
            # Unfortunately, Finnhub's free tier doesn't provide options data
            # We'll return a placeholder and log a warning
            logger.warning(f"Options data not available in Finnhub free tier for {symbol}")
            
            # Get current stock price for reference
            quote = self.get_real_time_data(symbol)
            current_price = quote.get('c', 0)
            
            # Return empty options chain with current price
            return {
                'symbol': symbol,
                'current_price': current_price,
                'expiry': None,
                'calls': pd.DataFrame(),
                'puts': pd.DataFrame()
            }
            
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol}: {e}")
            return {}
    
    def _convert_interval_to_resolution(self, interval):
        """
        Convert interval string to Finnhub resolution
        
        Args:
            interval (str): Data interval (e.g., '1m', '5m', '15m', '1h', '1d')
            
        Returns:
            str: Finnhub resolution
        """
        if interval.endswith('m'):
            minutes = int(interval[:-1])
            if minutes == 1:
                return '1'
            elif minutes == 5:
                return '5'
            elif minutes == 15:
                return '15'
            elif minutes == 30:
                return '30'
            else:
                return 'D'  # Default to daily
        elif interval.endswith('h'):
            hours = int(interval[:-1])
            if hours == 1:
                return '60'
            else:
                return 'D'  # Default to daily
        elif interval.endswith('d'):
            return 'D'
        elif interval.endswith('w'):
            return 'W'
        elif interval.endswith('mo'):
            return 'M'
        else:
            return 'D'  # Default to daily
