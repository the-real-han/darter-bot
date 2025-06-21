#!/usr/bin/env python3
"""
Base Data Provider Module
-----------------------
Defines the interface for market data providers
"""

from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime, timedelta

class BaseDataProvider(ABC):
    """Base class for market data providers"""
    
    def __init__(self, api_key=None, **kwargs):
        """
        Initialize the data provider
        
        Args:
            api_key (str): API key for the data provider
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.client = None
        self.initialize_client(**kwargs)
    
    @abstractmethod
    def initialize_client(self, **kwargs):
        """Initialize the API client"""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_real_time_data(self, symbol):
        """
        Get real-time market data for a symbol
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Real-time market data
        """
        pass
    
    @abstractmethod
    def get_options_chain(self, symbol):
        """
        Get options chain data for a symbol
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Options chain data
        """
        pass
    
    def convert_period_to_days(self, period):
        """
        Convert period string to number of days
        
        Args:
            period (str): Time period (e.g., '1d', '5d', '1mo', '3mo', '1y')
            
        Returns:
            int: Number of days
        """
        if period.endswith('d'):
            return int(period[:-1])
        elif period.endswith('mo'):
            return int(period[:-2]) * 30
        elif period.endswith('y'):
            return int(period[:-1]) * 365
        else:
            return 90  # Default to 3 months
    
    def convert_interval_to_minutes(self, interval):
        """
        Convert interval string to number of minutes
        
        Args:
            interval (str): Data interval (e.g., '1m', '5m', '15m', '1h', '1d')
            
        Returns:
            int: Number of minutes
        """
        if interval.endswith('m'):
            return int(interval[:-1])
        elif interval.endswith('h'):
            return int(interval[:-1]) * 60
        elif interval.endswith('d'):
            return int(interval[:-1]) * 1440  # 24 * 60
        else:
            return 1440  # Default to daily
