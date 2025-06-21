#!/usr/bin/env python3
"""
Polygon.io Data Provider Module
----------------------------
Implements the Polygon.io market data provider for options data
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from .base_provider import BaseDataProvider

logger = logging.getLogger('trading_bot.data_providers.polygon')

class PolygonDataProvider(BaseDataProvider):
    """Polygon.io market data provider implementation"""
    
    BASE_URL = "https://api.polygon.io"
    
    def initialize_client(self, **kwargs):
        """Initialize the Polygon.io API client"""
        try:
            self.client = True  # Placeholder for client
            self.last_api_call = 0  # For rate limiting
            logger.info("Polygon.io client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Polygon.io client: {e}")
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
        if not self.api_key:
            logger.error("API key is required for Polygon.io")
            return pd.DataFrame()
        
        try:
            # Convert period to days and calculate start date
            days = self.convert_period_to_days(period)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Convert interval to Polygon.io timespan
            timespan, multiplier = self._convert_interval_to_timespan(interval)
            
            # Respect rate limits (5 calls per minute for free tier)
            self._respect_rate_limit()
            
            # Fetch data from Polygon.io
            url = f"{self.BASE_URL}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date_str}/{end_date_str}?apiKey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if 'results' not in data or not data['results']:
                logger.warning(f"No data available for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            results = data['results']
            df = pd.DataFrame(results)
            
            # Rename columns to match our standard format
            df = df.rename(columns={
                'o': 'Open',
                'h': 'High',
                'l': 'Low',
                'c': 'Close',
                'v': 'Volume',
                't': 'timestamp'
            })
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
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
        if not self.api_key:
            logger.error("API key is required for Polygon.io")
            return {}
        
        try:
            # Respect rate limits (5 calls per minute for free tier)
            self._respect_rate_limit()
            
            # Get real-time quote
            url = f"{self.BASE_URL}/v2/last/trade/{symbol}?apiKey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if 'results' not in data:
                logger.warning(f"No real-time data available for {symbol}")
                return {}
            
            result = data['results']
            
            # Format as a quote dictionary
            quote = {
                'c': result['p'],  # Current price
                'h': result['p'],  # High price (using last price as placeholder)
                'l': result['p'],  # Low price (using last price as placeholder)
                'o': result['p'],  # Open price (using last price as placeholder)
                'pc': result['p'],  # Previous close (using last price as placeholder)
                'timestamp': datetime.fromtimestamp(result['t'] / 1000)  # Timestamp
            }
            
            logger.info(f"Fetched real-time data for {symbol}")
            return quote
            
        except Exception as e:
            logger.error(f"Error fetching real-time data for {symbol}: {e}")
            return {}
    
    def get_options_chain(self, symbol):
        """
        Get options chain data for a symbol using Polygon.io's snapshot API
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Options chain data with Greeks
        """
        if not self.api_key:
            logger.error("API key is required for Polygon.io")
            return {}
        
        try:
            # Respect rate limits
            self._respect_rate_limit()
            
            # Get current stock price
            quote = self.get_real_time_data(symbol)
            current_price = quote.get('c', 0)
            
            # Get options snapshot
            url = f"{self.BASE_URL}/v3/snapshot/options/{symbol}?apiKey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if 'results' not in data or not data['results']:
                logger.warning(f"No options data available for {symbol}")
                return {}
            
            # Process options data
            results = data['results']
            calls_data = []
            puts_data = []
            expirations = set()
            
            for contract in results:
                # Extract expiration date
                expiry = contract.get('expiration_date')
                if expiry:
                    expirations.add(expiry)
                
                # Separate calls and puts
                if contract.get('contract_type') == 'call':
                    calls_data.append(contract)
                else:
                    puts_data.append(contract)
            
            # Sort expirations and get the nearest one
            expirations = sorted(list(expirations))
            if not expirations:
                return {}
            
            expiry = expirations[0]
            
            # Filter for nearest expiration
            calls = [c for c in calls_data if c.get('expiration_date') == expiry]
            puts = [p for p in puts_data if p.get('expiration_date') == expiry]
            
            # Convert to DataFrames
            calls_df = pd.DataFrame(calls)
            puts_df = pd.DataFrame(puts)
            
            # Rename columns to match our standard format
            column_mapping = {
                'strike_price': 'strike',
                'last_price': 'lastPrice',
                'implied_volatility': 'impliedVolatility',
                'delta': 'delta',
                'gamma': 'gamma',
                'theta': 'theta',
                'vega': 'vega',
                'rho': 'rho',
                'open_interest': 'openInterest',
                'volume': 'volume'
            }
            
            if not calls_df.empty:
                calls_df = calls_df.rename(columns=column_mapping)
            
            if not puts_df.empty:
                puts_df = puts_df.rename(columns=column_mapping)
            
            options_data = {
                'symbol': symbol,
                'current_price': current_price,
                'expiry': expiry,
                'calls': calls_df,
                'puts': puts_df
            }
            
            logger.info(f"Fetched options chain with Greeks for {symbol} with expiry {expiry}")
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol}: {e}")
            return {}
    
    def _enrich_options_prices(self, options_data):
        """
        Enrich options data with actual prices
        
        Args:
            options_data (dict): Options data to enrich
        """
        symbol = options_data['symbol']
        expiry = options_data['expiry']
        current_price = options_data['current_price']
        calls = options_data['calls']
        puts = options_data['puts']
        
        try:
            # Find ATM strikes
            if not calls.empty and 'strike' in calls.columns:
                calls['strike_diff'] = abs(calls['strike'] - current_price)
                atm_call_idx = calls['strike_diff'].idxmin()
                atm_call_strike = calls.loc[atm_call_idx, 'strike']
                
                # Get ATM call price
                self._respect_rate_limit()
                call_ticker = f"O:{symbol}{expiry.replace('-', '')}C{int(atm_call_strike * 1000):08d}"
                url = f"{self.BASE_URL}/v2/last/trade/{call_ticker}?apiKey={self.api_key}"
                response = requests.get(url)
                data = response.json()
                
                if 'results' in data:
                    atm_call_price = data['results']['p']
                    calls.loc[atm_call_idx, 'lastPrice'] = atm_call_price
            
            if not puts.empty and 'strike' in puts.columns:
                puts['strike_diff'] = abs(puts['strike'] - current_price)
                atm_put_idx = puts['strike_diff'].idxmin()
                atm_put_strike = puts.loc[atm_put_idx, 'strike']
                
                # Get ATM put price
                self._respect_rate_limit()
                put_ticker = f"O:{symbol}{expiry.replace('-', '')}P{int(atm_put_strike * 1000):08d}"
                url = f"{self.BASE_URL}/v2/last/trade/{put_ticker}?apiKey={self.api_key}"
                response = requests.get(url)
                data = response.json()
                
                if 'results' in data:
                    atm_put_price = data['results']['p']
                    puts.loc[atm_put_idx, 'lastPrice'] = atm_put_price
            
            logger.info(f"Enriched options prices for {symbol}")
            
        except Exception as e:
            logger.error(f"Error enriching options prices for {symbol}: {e}")
    
    def _convert_interval_to_timespan(self, interval):
        """
        Convert interval string to Polygon.io timespan
        
        Args:
            interval (str): Data interval (e.g., '1m', '5m', '15m', '1h', '1d')
            
        Returns:
            tuple: (timespan, multiplier)
        """
        if interval.endswith('m'):
            return 'minute', interval[:-1]
        elif interval.endswith('h'):
            return 'hour', interval[:-1]
        elif interval.endswith('d'):
            return 'day', interval[:-1]
        elif interval.endswith('w'):
            return 'week', interval[:-1]
        elif interval.endswith('mo'):
            return 'month', interval[:-2]
        else:
            return 'day', '1'  # Default to daily
    
    def _respect_rate_limit(self):
        """Respect Polygon.io API rate limits (5 calls per minute for free tier)"""
        current_time = time.time()
        elapsed = current_time - self.last_api_call
        
        # If less than 12 seconds since last call, wait
        if elapsed < 12:
            time.sleep(12 - elapsed)
        
        self.last_api_call = time.time()
