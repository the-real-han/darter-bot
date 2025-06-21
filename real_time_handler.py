#!/usr/bin/env python3
"""
Real-Time Data Handler Module
--------------------------
Handles real-time market data processing
"""

import os
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from data_providers.provider_factory import DataProviderFactory

logger = logging.getLogger('trading_bot.real_time')

class RealTimeHandler:
    def __init__(self, provider_name='finnhub', api_key=None, update_interval=60, **kwargs):
        """
        Initialize the real-time data handler
        
        Args:
            provider_name (str): Name of the data provider
            api_key (str): API key for the data provider
            update_interval (int): Interval in seconds between data updates
            **kwargs: Additional provider-specific parameters
        """
        self.provider_name = provider_name
        self.api_key = api_key
        self.update_interval = update_interval
        self.provider_kwargs = kwargs
        
        # Initialize data provider
        self.provider = DataProviderFactory.get_provider(provider_name, api_key, **kwargs)
        
        # Data containers
        self.historical_data = {}
        self.real_time_data = {}
        self.options_data = {}
        self.last_update_time = {}
    
    def initialize_data(self, symbols, period='3mo', interval='1d'):
        """
        Initialize historical data for symbols
        
        Args:
            symbols (list): List of stock symbols
            period (str): Time period for historical data
            interval (str): Data interval for historical data
            
        Returns:
            dict: Dictionary of historical data for each symbol
        """
        logger.info(f"Initializing historical data for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                # Fetch historical data
                df = self.provider.get_historical_data(symbol, period, interval)
                
                if not df.empty:
                    self.historical_data[symbol] = df
                    self.last_update_time[symbol] = datetime.now()
                    logger.info(f"Initialized historical data for {symbol} with {len(df)} data points")
                else:
                    logger.warning(f"No historical data available for {symbol}")
            except Exception as e:
                logger.error(f"Error initializing data for {symbol}: {e}")
        
        return self.historical_data
    
    def update_real_time_data(self, symbols):
        """
        Update real-time data for symbols
        
        Args:
            symbols (list): List of stock symbols
            
        Returns:
            dict: Dictionary of real-time data for each symbol
        """
        logger.info(f"Updating real-time data for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                # Check if we need to update (based on update interval)
                current_time = datetime.now()
                last_update = self.last_update_time.get(symbol, datetime.min)
                
                if (current_time - last_update).total_seconds() >= self.update_interval:
                    # Fetch real-time data
                    quote = self.provider.get_real_time_data(symbol)
                    
                    if quote:
                        self.real_time_data[symbol] = quote
                        self.last_update_time[symbol] = current_time
                        logger.info(f"Updated real-time data for {symbol}")
                        
                        # Update the last row of historical data if available
                        if symbol in self.historical_data and not self.historical_data[symbol].empty:
                            last_date = self.historical_data[symbol].index[-1].date()
                            current_date = datetime.now().date()
                            
                            if last_date == current_date:
                                # Update the last row with real-time data
                                self.historical_data[symbol].loc[self.historical_data[symbol].index[-1], 'Close'] = quote['c']
                                self.historical_data[symbol].loc[self.historical_data[symbol].index[-1], 'High'] = max(
                                    self.historical_data[symbol].loc[self.historical_data[symbol].index[-1], 'High'],
                                    quote['c']
                                )
                                self.historical_data[symbol].loc[self.historical_data[symbol].index[-1], 'Low'] = min(
                                    self.historical_data[symbol].loc[self.historical_data[symbol].index[-1], 'Low'],
                                    quote['c']
                                )
                    else:
                        logger.warning(f"No real-time data available for {symbol}")
            except Exception as e:
                logger.error(f"Error updating real-time data for {symbol}: {e}")
        
        return self.real_time_data
    
    def update_options_data(self, symbols):
        """
        Update options data for symbols
        
        Args:
            symbols (list): List of stock symbols
            
        Returns:
            dict: Dictionary of options data for each symbol
        """
        logger.info(f"Updating options data for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                # Check if we need to update (based on update interval)
                current_time = datetime.now()
                last_update = self.last_update_time.get(f"{symbol}_options", datetime.min)
                
                if (current_time - last_update).total_seconds() >= self.update_interval:
                    # Fetch options data
                    options_data = self.provider.get_options_chain(symbol)
                    
                    if options_data:
                        self.options_data[symbol] = options_data
                        self.last_update_time[f"{symbol}_options"] = current_time
                        logger.info(f"Updated options data for {symbol}")
                    else:
                        logger.warning(f"No options data available for {symbol}")
            except Exception as e:
                logger.error(f"Error updating options data for {symbol}: {e}")
        
        return self.options_data
    
    def get_latest_data(self, symbol):
        """
        Get the latest data for a symbol
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Latest data including historical, real-time, and options data
        """
        result = {
            'symbol': symbol,
            'historical_data': self.historical_data.get(symbol, pd.DataFrame()),
            'real_time_data': self.real_time_data.get(symbol, {}),
            'options_data': self.options_data.get(symbol, {}),
            'last_update': self.last_update_time.get(symbol, None)
        }
        
        return result
    
    def run_update_loop(self, symbols, callback=None, run_once=False):
        """
        Run a continuous update loop for real-time data
        
        Args:
            symbols (list): List of stock symbols
            callback (function): Callback function to call after each update
            run_once (bool): Whether to run the update loop once or continuously
        """
        try:
            while True:
                # Update real-time data
                self.update_real_time_data(symbols)
                
                # Update options data
                self.update_options_data(symbols)
                
                # Call callback function if provided
                if callback:
                    callback(self.historical_data, self.real_time_data, self.options_data)
                
                # Break if run_once is True
                if run_once:
                    break
                
                # Sleep for update interval
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            logger.info("Update loop interrupted by user")
        except Exception as e:
            logger.error(f"Error in update loop: {e}")
    
    def save_data(self, output_dir):
        """
        Save current data to CSV files
        
        Args:
            output_dir (str): Directory to save data files
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Save historical data
            for symbol, df in self.historical_data.items():
                if not df.empty:
                    file_path = os.path.join(output_dir, f"{symbol}_historical.csv")
                    df.to_csv(file_path)
                    logger.info(f"Saved historical data for {symbol} to {file_path}")
            
            # Save real-time data
            real_time_df = pd.DataFrame.from_dict(self.real_time_data, orient='index')
            if not real_time_df.empty:
                file_path = os.path.join(output_dir, "real_time_data.csv")
                real_time_df.to_csv(file_path)
                logger.info(f"Saved real-time data to {file_path}")
            
            # Save last update times
            update_times_df = pd.DataFrame.from_dict(
                {k: {'last_update': v} for k, v in self.last_update_time.items()},
                orient='index'
            )
            if not update_times_df.empty:
                file_path = os.path.join(output_dir, "update_times.csv")
                update_times_df.to_csv(file_path)
                logger.info(f"Saved update times to {file_path}")
                
        except Exception as e:
            logger.error(f"Error saving data: {e}")
