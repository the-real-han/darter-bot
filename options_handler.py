#!/usr/bin/env python3
"""
Options Handler Module for Trading Bot
------------------------------------
Implements options trading functionality
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('trading_bot.options')

class OptionsHandler:
    def __init__(self):
        """Initialize the options handler"""
        self.options_data = {}
    
    def fetch_options_chain(self, symbol):
        """
        Fetch options chain data for a symbol
        
        Args:
            symbol (str): Stock symbol to fetch options for
            
        Returns:
            dict: Dictionary with calls and puts DataFrames
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates
            expirations = ticker.options
            
            if not expirations:
                logger.warning(f"No options available for {symbol}")
                return None
            
            # Get options for the first expiration date
            expiry = expirations[0]
            
            # Fetch options chain
            options = ticker.option_chain(expiry)
            
            self.options_data[symbol] = {
                'expiry': expiry,
                'calls': options.calls,
                'puts': options.puts
            }
            
            logger.info(f"Fetched options chain for {symbol} with expiry {expiry}")
            return self.options_data[symbol]
            
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol}: {e}")
            return None
    
    def fetch_all_expirations(self, symbol):
        """
        Fetch all available options expirations for a symbol
        
        Args:
            symbol (str): Stock symbol to fetch options for
            
        Returns:
            dict: Dictionary with options data for all expirations
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates
            expirations = ticker.options
            
            if not expirations:
                logger.warning(f"No options available for {symbol}")
                return None
            
            all_options = {}
            
            for expiry in expirations:
                # Fetch options chain
                options = ticker.option_chain(expiry)
                
                all_options[expiry] = {
                    'calls': options.calls,
                    'puts': options.puts
                }
            
            logger.info(f"Fetched all options expirations for {symbol}")
            return all_options
            
        except Exception as e:
            logger.error(f"Error fetching all options data for {symbol}: {e}")
            return None
    
    def find_atm_options(self, symbol, current_price=None):
        """
        Find at-the-money options for a symbol
        
        Args:
            symbol (str): Stock symbol
            current_price (float): Current stock price (if None, fetch from yfinance)
            
        Returns:
            dict: Dictionary with ATM call and put options
        """
        if symbol not in self.options_data:
            self.fetch_options_chain(symbol)
            
        if symbol not in self.options_data:
            return None
            
        if current_price is None:
            try:
                ticker = yf.Ticker(symbol)
                current_price = ticker.history(period='1d')['Close'].iloc[-1]
            except Exception as e:
                logger.error(f"Error fetching current price for {symbol}: {e}")
                return None
        
        calls = self.options_data[symbol]['calls']
        puts = self.options_data[symbol]['puts']
        
        # Find closest strike to current price
        calls['strike_diff'] = abs(calls['strike'] - current_price)
        puts['strike_diff'] = abs(puts['strike'] - current_price)
        
        atm_call = calls.loc[calls['strike_diff'].idxmin()]
        atm_put = puts.loc[puts['strike_diff'].idxmin()]
        
        return {
            'current_price': current_price,
            'expiry': self.options_data[symbol]['expiry'],
            'atm_call': atm_call,
            'atm_put': atm_put
        }
    
    def calculate_implied_volatility(self, symbol):
        """
        Calculate implied volatility for options
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            dict: Dictionary with implied volatility data
        """
        if symbol not in self.options_data:
            self.fetch_options_chain(symbol)
            
        if symbol not in self.options_data:
            return None
        
        calls = self.options_data[symbol]['calls']
        puts = self.options_data[symbol]['puts']
        
        # Calculate average implied volatility
        avg_call_iv = calls['impliedVolatility'].mean()
        avg_put_iv = puts['impliedVolatility'].mean()
        
        return {
            'expiry': self.options_data[symbol]['expiry'],
            'avg_call_iv': avg_call_iv,
            'avg_put_iv': avg_put_iv,
            'avg_iv': (avg_call_iv + avg_put_iv) / 2
        }
    
    def options_strategy_signals(self, symbol, stock_signal, current_price=None):
        """
        Generate options trading signals based on stock signals
        
        Args:
            symbol (str): Stock symbol
            stock_signal (int): Stock trading signal (1: buy, -1: sell, 0: hold)
            current_price (float): Current stock price (if None, fetch from yfinance)
            
        Returns:
            dict: Dictionary with options trading signals
        """
        if current_price is None:
            try:
                ticker = yf.Ticker(symbol)
                current_price = ticker.history(period='1d')['Close'].iloc[-1]
            except Exception as e:
                logger.error(f"Error fetching current price for {symbol}: {e}")
                return None
        
        # Fetch options data if not already available
        if symbol not in self.options_data:
            self.fetch_options_chain(symbol)
            
        if symbol not in self.options_data:
            return None
        
        atm_options = self.find_atm_options(symbol, current_price)
        if atm_options is None:
            return None
        
        # Generate options signals based on stock signal
        if stock_signal > 0:  # Bullish
            return {
                'signal': 'BULLISH',
                'strategy': 'BUY_CALL',
                'option': atm_options['atm_call'],
                'expiry': atm_options['expiry'],
                'current_price': current_price
            }
        elif stock_signal < 0:  # Bearish
            return {
                'signal': 'BEARISH',
                'strategy': 'BUY_PUT',
                'option': atm_options['atm_put'],
                'expiry': atm_options['expiry'],
                'current_price': current_price
            }
        else:  # Neutral
            return {
                'signal': 'NEUTRAL',
                'strategy': 'IRON_CONDOR',
                'call': atm_options['atm_call'],
                'put': atm_options['atm_put'],
                'expiry': atm_options['expiry'],
                'current_price': current_price
            }
