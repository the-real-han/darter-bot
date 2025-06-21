#!/usr/bin/env python3
"""
Greek Optimizer Module
-------------------
Optimizes options trading strategies based on Greeks
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('trading_bot.greek_optimizer')

class GreekOptimizer:
    """Optimizes options trading strategies based on Greeks"""
    
    def __init__(self, config=None):
        """
        Initialize the Greek optimizer
        
        Args:
            config (dict): Configuration parameters
        """
        self.config = config or {}
        
        # Default configuration
        self.default_config = {
            'delta_threshold': 0.5,      # Delta threshold for directional trades
            'gamma_threshold': 0.1,      # Gamma threshold for acceleration trades
            'theta_threshold': -0.1,     # Theta threshold for time decay trades
            'vega_threshold': 0.2,       # Vega threshold for volatility trades
            'min_open_interest': 100,    # Minimum open interest for liquidity
            'min_volume': 10,            # Minimum volume for liquidity
            'max_bid_ask_spread': 0.1,   # Maximum bid-ask spread as percentage of price
            'risk_per_trade': 0.02       # Risk per trade as percentage of account
        }
        
        # Merge with provided config
        if self.config:
            for key, value in self.default_config.items():
                if key not in self.config:
                    self.config[key] = value
        else:
            self.config = self.default_config.copy()
            
        logger.info("Greek optimizer initialized")
    
    def optimize_directional_trade(self, options_data, direction, risk_capital):
        """
        Optimize a directional options trade based on Greeks
        
        Args:
            options_data (dict): Options data with Greeks
            direction (str): Trade direction ('bullish' or 'bearish')
            risk_capital (float): Capital available for the trade
            
        Returns:
            dict: Optimized trade parameters
        """
        if direction not in ['bullish', 'bearish']:
            logger.error(f"Invalid direction: {direction}")
            return None
        
        try:
            # Select calls for bullish, puts for bearish
            if direction == 'bullish':
                options_df = options_data.get('calls', pd.DataFrame())
                target_delta = self.config['delta_threshold']  # Higher delta for directional exposure
            else:
                options_df = options_data.get('puts', pd.DataFrame())
                target_delta = self.config['delta_threshold']  # Higher delta for directional exposure
            
            if options_df.empty:
                logger.warning(f"No {direction} options data available")
                return None
            
            # Filter for liquidity
            liquid_options = options_df[
                (options_df.get('openInterest', 0) >= self.config['min_open_interest']) & 
                (options_df.get('volume', 0) >= self.config['min_volume'])
            ]
            
            if liquid_options.empty:
                logger.warning("No options meet liquidity criteria")
                liquid_options = options_df  # Fall back to all options
            
            # Calculate score based on Greeks
            liquid_options['delta_score'] = liquid_options.get('delta', 0.5).apply(
                lambda x: 1 - abs(x - target_delta)
            )
            
            # Gamma score - prefer higher gamma for directional trades
            liquid_options['gamma_score'] = liquid_options.get('gamma', 0).apply(
                lambda x: min(x / self.config['gamma_threshold'], 1)
            )
            
            # Theta score - prefer less negative theta
            liquid_options['theta_score'] = liquid_options.get('theta', 0).apply(
                lambda x: min(1, max(0, (x - self.config['theta_threshold']) / abs(self.config['theta_threshold'])))
            )
            
            # Calculate total score
            liquid_options['total_score'] = (
                liquid_options['delta_score'] * 0.5 +
                liquid_options['gamma_score'] * 0.3 +
                liquid_options['theta_score'] * 0.2
            )
            
            # Get the best option
            best_option = liquid_options.loc[liquid_options['total_score'].idxmax()]
            
            # Calculate position size
            option_price = best_option.get('lastPrice', 1.0)
            max_contracts = int(risk_capital / (option_price * 100))  # Each contract is 100 shares
            
            if max_contracts < 1:
                logger.warning("Insufficient capital for even one contract")
                max_contracts = 1
            
            # Create trade parameters
            trade = {
                'symbol': options_data.get('symbol'),
                'expiry': options_data.get('expiry'),
                'strike': best_option.get('strike'),
                'option_type': 'call' if direction == 'bullish' else 'put',
                'contracts': max_contracts,
                'price': option_price,
                'delta': best_option.get('delta'),
                'gamma': best_option.get('gamma'),
                'theta': best_option.get('theta'),
                'vega': best_option.get('vega'),
                'score': best_option.get('total_score'),
                'strategy': 'directional',
                'direction': direction
            }
            
            logger.info(f"Optimized {direction} trade: {trade['contracts']} contracts of {trade['symbol']} {trade['strike']} {trade['option_type']}")
            return trade
            
        except Exception as e:
            logger.error(f"Error optimizing directional trade: {e}")
            return None
    
    def optimize_volatility_trade(self, options_data, volatility_outlook, risk_capital):
        """
        Optimize a volatility-based options trade based on Greeks
        
        Args:
            options_data (dict): Options data with Greeks
            volatility_outlook (str): Volatility outlook ('increasing' or 'decreasing')
            risk_capital (float): Capital available for the trade
            
        Returns:
            dict: Optimized trade parameters
        """
        if volatility_outlook not in ['increasing', 'decreasing']:
            logger.error(f"Invalid volatility outlook: {volatility_outlook}")
            return None
        
        try:
            # Get calls and puts
            calls = options_data.get('calls', pd.DataFrame())
            puts = options_data.get('puts', pd.DataFrame())
            
            if calls.empty or puts.empty:
                logger.warning("Insufficient options data for volatility trade")
                return None
            
            # For increasing volatility: long straddle/strangle (high vega)
            # For decreasing volatility: short straddle/strangle or iron condor (negative vega)
            
            # Find ATM options
            current_price = options_data.get('current_price', 0)
            
            if current_price == 0:
                logger.warning("Current price not available")
                return None
            
            calls['strike_diff'] = abs(calls['strike'] - current_price)
            puts['strike_diff'] = abs(puts['strike'] - current_price)
            
            # Get ATM call and put
            atm_call = calls.loc[calls['strike_diff'].idxmin()]
            atm_put = puts.loc[puts['strike_diff'].idxmin()]
            
            if volatility_outlook == 'increasing':
                # Long straddle: buy ATM call and put
                call_price = atm_call.get('lastPrice', 1.0)
                put_price = atm_put.get('lastPrice', 1.0)
                total_price = call_price + put_price
                
                # Calculate position size
                max_contracts = int(risk_capital / (total_price * 100))
                
                if max_contracts < 1:
                    logger.warning("Insufficient capital for straddle")
                    max_contracts = 1
                
                trade = {
                    'symbol': options_data.get('symbol'),
                    'expiry': options_data.get('expiry'),
                    'strategy': 'long_straddle',
                    'call_strike': atm_call.get('strike'),
                    'put_strike': atm_put.get('strike'),
                    'contracts': max_contracts,
                    'call_price': call_price,
                    'put_price': put_price,
                    'total_price': total_price,
                    'call_vega': atm_call.get('vega'),
                    'put_vega': atm_put.get('vega'),
                    'total_vega': atm_call.get('vega', 0) + atm_put.get('vega', 0),
                    'direction': 'long_volatility'
                }
                
                logger.info(f"Optimized long volatility trade: {trade['contracts']} contracts of {trade['symbol']} straddle at {trade['call_strike']}")
                return trade
                
            else:  # decreasing volatility
                # Iron condor: sell OTM call and put, buy further OTM call and put
                
                # Find OTM options
                otm_calls = calls[calls['strike'] > current_price].sort_values('strike')
                otm_puts = puts[puts['strike'] < current_price].sort_values('strike', ascending=False)
                
                if otm_calls.empty or otm_puts.empty:
                    logger.warning("Insufficient OTM options for iron condor")
                    return None
                
                # Select options with appropriate delta
                target_delta = 0.25  # Common delta for iron condor short legs
                
                otm_calls['delta_diff'] = abs(otm_calls.get('delta', 0.5) - target_delta)
                otm_puts['delta_diff'] = abs(otm_puts.get('delta', 0.5) - target_delta)
                
                short_call = otm_calls.loc[otm_calls['delta_diff'].idxmin()]
                short_put = otm_puts.loc[otm_puts['delta_diff'].idxmin()]
                
                # Find further OTM options for long legs
                further_otm_calls = calls[calls['strike'] > short_call['strike']].sort_values('strike')
                further_otm_puts = puts[puts['strike'] < short_put['strike']].sort_values('strike', ascending=False)
                
                if further_otm_calls.empty or further_otm_puts.empty:
                    logger.warning("Insufficient further OTM options for iron condor")
                    return None
                
                long_call = further_otm_calls.iloc[0]
                long_put = further_otm_puts.iloc[0]
                
                # Calculate net credit
                short_call_price = short_call.get('lastPrice', 1.0)
                short_put_price = short_put.get('lastPrice', 1.0)
                long_call_price = long_call.get('lastPrice', 0.5)
                long_put_price = long_put.get('lastPrice', 0.5)
                
                net_credit = (short_call_price + short_put_price) - (long_call_price + long_put_price)
                
                # Calculate max risk
                call_spread_width = long_call['strike'] - short_call['strike']
                put_spread_width = short_put['strike'] - long_put['strike']
                max_risk = max(call_spread_width, put_spread_width) - net_credit
                
                # Calculate position size
                max_contracts = int(risk_capital / (max_risk * 100))
                
                if max_contracts < 1:
                    logger.warning("Insufficient capital for iron condor")
                    max_contracts = 1
                
                trade = {
                    'symbol': options_data.get('symbol'),
                    'expiry': options_data.get('expiry'),
                    'strategy': 'iron_condor',
                    'short_call_strike': short_call.get('strike'),
                    'long_call_strike': long_call.get('strike'),
                    'short_put_strike': short_put.get('strike'),
                    'long_put_strike': long_put.get('strike'),
                    'contracts': max_contracts,
                    'net_credit': net_credit,
                    'max_risk': max_risk,
                    'short_call_delta': short_call.get('delta'),
                    'short_put_delta': short_put.get('delta'),
                    'total_vega': -(short_call.get('vega', 0) + short_put.get('vega', 0)) + (long_call.get('vega', 0) + long_put.get('vega', 0)),
                    'direction': 'short_volatility'
                }
                
                logger.info(f"Optimized short volatility trade: {trade['contracts']} contracts of {trade['symbol']} iron condor")
                return trade
                
        except Exception as e:
            logger.error(f"Error optimizing volatility trade: {e}")
            return None
    
    def optimize_theta_decay_trade(self, options_data, risk_capital):
        """
        Optimize a theta decay options trade based on Greeks
        
        Args:
            options_data (dict): Options data with Greeks
            risk_capital (float): Capital available for the trade
            
        Returns:
            dict: Optimized trade parameters
        """
        try:
            # Get calls and puts
            calls = options_data.get('calls', pd.DataFrame())
            puts = options_data.get('puts', pd.DataFrame())
            
            if calls.empty or puts.empty:
                logger.warning("Insufficient options data for theta decay trade")
                return None
            
            # For theta decay: credit spread (high negative theta)
            
            # Find options with high theta decay
            calls['theta_score'] = calls.get('theta', 0).apply(lambda x: abs(x) if x < 0 else 0)
            puts['theta_score'] = puts.get('theta', 0).apply(lambda x: abs(x) if x < 0 else 0)
            
            # Filter for liquidity
            liquid_calls = calls[
                (calls.get('openInterest', 0) >= self.config['min_open_interest']) & 
                (calls.get('volume', 0) >= self.config['min_volume'])
            ]
            
            liquid_puts = puts[
                (puts.get('openInterest', 0) >= self.config['min_open_interest']) & 
                (puts.get('volume', 0) >= self.config['min_volume'])
            ]
            
            if liquid_calls.empty and liquid_puts.empty:
                logger.warning("No options meet liquidity criteria for theta decay trade")
                return None
            
            # Determine which has better theta decay opportunities
            if not liquid_calls.empty and not liquid_puts.empty:
                best_call_theta = liquid_calls['theta_score'].max()
                best_put_theta = liquid_puts['theta_score'].max()
                
                if best_call_theta >= best_put_theta:
                    # Use call credit spread
                    return self._create_call_credit_spread(liquid_calls, options_data, risk_capital)
                else:
                    # Use put credit spread
                    return self._create_put_credit_spread(liquid_puts, options_data, risk_capital)
            elif not liquid_calls.empty:
                return self._create_call_credit_spread(liquid_calls, options_data, risk_capital)
            else:
                return self._create_put_credit_spread(liquid_puts, options_data, risk_capital)
                
        except Exception as e:
            logger.error(f"Error optimizing theta decay trade: {e}")
            return None
    
    def _create_call_credit_spread(self, calls, options_data, risk_capital):
        """Create a call credit spread for theta decay"""
        # Sort by theta score
        calls = calls.sort_values('theta_score', ascending=False)
        
        # Get the option with highest theta decay
        short_call = calls.iloc[0]
        
        # Find a further OTM call for the long leg
        long_calls = calls[calls['strike'] > short_call['strike']].sort_values('strike')
        
        if long_calls.empty:
            logger.warning("No suitable long call available for credit spread")
            return None
        
        long_call = long_calls.iloc[0]
        
        # Calculate net credit
        short_call_price = short_call.get('lastPrice', 1.0)
        long_call_price = long_call.get('lastPrice', 0.5)
        net_credit = short_call_price - long_call_price
        
        # Calculate max risk
        max_risk = (long_call['strike'] - short_call['strike']) - net_credit
        
        # Calculate position size
        max_contracts = int(risk_capital / (max_risk * 100))
        
        if max_contracts < 1:
            logger.warning("Insufficient capital for call credit spread")
            max_contracts = 1
        
        trade = {
            'symbol': options_data.get('symbol'),
            'expiry': options_data.get('expiry'),
            'strategy': 'call_credit_spread',
            'short_strike': short_call.get('strike'),
            'long_strike': long_call.get('strike'),
            'contracts': max_contracts,
            'net_credit': net_credit,
            'max_risk': max_risk,
            'short_theta': short_call.get('theta'),
            'long_theta': long_call.get('theta'),
            'net_theta': short_call.get('theta', 0) - long_call.get('theta', 0),
            'direction': 'theta_decay'
        }
        
        logger.info(f"Optimized theta decay trade: {trade['contracts']} contracts of {trade['symbol']} call credit spread")
        return trade
    
    def _create_put_credit_spread(self, puts, options_data, risk_capital):
        """Create a put credit spread for theta decay"""
        # Sort by theta score
        puts = puts.sort_values('theta_score', ascending=False)
        
        # Get the option with highest theta decay
        short_put = puts.iloc[0]
        
        # Find a further OTM put for the long leg
        long_puts = puts[puts['strike'] < short_put['strike']].sort_values('strike', ascending=False)
        
        if long_puts.empty:
            logger.warning("No suitable long put available for credit spread")
            return None
        
        long_put = long_puts.iloc[0]
        
        # Calculate net credit
        short_put_price = short_put.get('lastPrice', 1.0)
        long_put_price = long_put.get('lastPrice', 0.5)
        net_credit = short_put_price - long_put_price
        
        # Calculate max risk
        max_risk = (short_put['strike'] - long_put['strike']) - net_credit
        
        # Calculate position size
        max_contracts = int(risk_capital / (max_risk * 100))
        
        if max_contracts < 1:
            logger.warning("Insufficient capital for put credit spread")
            max_contracts = 1
        
        trade = {
            'symbol': options_data.get('symbol'),
            'expiry': options_data.get('expiry'),
            'strategy': 'put_credit_spread',
            'short_strike': short_put.get('strike'),
            'long_strike': long_put.get('strike'),
            'contracts': max_contracts,
            'net_credit': net_credit,
            'max_risk': max_risk,
            'short_theta': short_put.get('theta'),
            'long_theta': long_put.get('theta'),
            'net_theta': short_put.get('theta', 0) - long_put.get('theta', 0),
            'direction': 'theta_decay'
        }
        
        logger.info(f"Optimized theta decay trade: {trade['contracts']} contracts of {trade['symbol']} put credit spread")
        return trade
    
    def optimize_gamma_scalping_trade(self, options_data, risk_capital):
        """
        Optimize a gamma scalping options trade based on Greeks
        
        Args:
            options_data (dict): Options data with Greeks
            risk_capital (float): Capital available for the trade
            
        Returns:
            dict: Optimized trade parameters
        """
        try:
            # Get calls and puts
            calls = options_data.get('calls', pd.DataFrame())
            
            if calls.empty:
                logger.warning("Insufficient options data for gamma scalping trade")
                return None
            
            # For gamma scalping: ATM options with high gamma
            
            # Find ATM options
            current_price = options_data.get('current_price', 0)
            
            if current_price == 0:
                logger.warning("Current price not available")
                return None
            
            calls['strike_diff'] = abs(calls['strike'] - current_price)
            
            # Filter for near ATM options
            near_atm_calls = calls[calls['strike_diff'] <= current_price * 0.05]
            
            if near_atm_calls.empty:
                logger.warning("No near ATM calls available for gamma scalping")
                near_atm_calls = calls  # Fall back to all calls
            
            # Sort by gamma
            near_atm_calls = near_atm_calls.sort_values('gamma', ascending=False)
            
            # Get the option with highest gamma
            best_call = near_atm_calls.iloc[0]
            
            # Calculate position size
            option_price = best_call.get('lastPrice', 1.0)
            max_contracts = int(risk_capital / (option_price * 100))
            
            if max_contracts < 1:
                logger.warning("Insufficient capital for gamma scalping")
                max_contracts = 1
            
            trade = {
                'symbol': options_data.get('symbol'),
                'expiry': options_data.get('expiry'),
                'strategy': 'gamma_scalping',
                'strike': best_call.get('strike'),
                'option_type': 'call',
                'contracts': max_contracts,
                'price': option_price,
                'delta': best_call.get('delta'),
                'gamma': best_call.get('gamma'),
                'theta': best_call.get('theta'),
                'vega': best_call.get('vega'),
                'direction': 'gamma_positive'
            }
            
            logger.info(f"Optimized gamma scalping trade: {trade['contracts']} contracts of {trade['symbol']} {trade['strike']} call")
            return trade
            
        except Exception as e:
            logger.error(f"Error optimizing gamma scalping trade: {e}")
            return None
