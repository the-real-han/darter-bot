#!/usr/bin/env python3
"""
Options Strategy Module for Trading Bot
-------------------------------------
Implements dedicated options trading strategies
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from strategy_config import load_strategy_config
from greek_optimizer import GreekOptimizer

logger = logging.getLogger('trading_bot.options_strategy')

class OptionsStrategy:
    def __init__(self, config_path=None):
        """
        Initialize the options strategy handler
        
        Args:
            config_path (str): Path to the strategy configuration file
        """
        self.signals = {}
        self.config = load_strategy_config(config_path)
        self.greek_optimizer = GreekOptimizer(self.config.get('greek_optimization', {}))
        logger.info("Options strategy initialized with configuration")
    
    def generate_signals(self, data_dict, options_data):
        """
        Generate options trading signals based on technical analysis
        
        Args:
            data_dict (dict): Dictionary of DataFrames with technical indicators
            options_data (dict): Dictionary of options data for each symbol
            
        Returns:
            dict: Dictionary of options trading signals
        """
        options_signals = {}
        
        for symbol, df in data_dict.items():
            try:
                if df is None or df.empty:
                    continue
                
                if symbol not in options_data:
                    logger.warning(f"No options data available for {symbol}")
                    continue
                
                # Get current price
                current_price = df['Close'].iloc[-1]
                
                # Generate signals based on technical indicators
                signal = self._analyze_technicals(df)
                
                # Find appropriate options based on the signal
                options_signal = self._select_options_strategy(symbol, signal, current_price, options_data[symbol])
                
                if options_signal:
                    options_signals[symbol] = options_signal
                    logger.info(f"Generated options signal for {symbol}: {options_signal['strategy']}")
                
            except Exception as e:
                logger.error(f"Error generating options signals for {symbol}: {e}")
        
        return options_signals
    
    def _analyze_technicals(self, df):
        """
        Analyze technical indicators to determine market direction
        
        Args:
            df (DataFrame): DataFrame with technical indicators
            
        Returns:
            str: Market direction signal ('bullish', 'bearish', or 'neutral')
        """
        # Get configuration for technical indicators
        tech_config = self.config.get('technical_indicators', {})
        signal_config = self.config.get('signals', {})
        
        # Initialize signal components
        signals = {
            'trend': 0,  # Trend component (moving averages)
            'momentum': 0,  # Momentum component (RSI, MACD)
            'volatility': 0  # Volatility component (Bollinger Bands)
        }
        
        # Trend analysis using moving averages
        if tech_config.get('use_sma', True):
            sma_periods = tech_config.get('sma_periods', [20, 50, 200])
            if len(sma_periods) >= 2:
                short_period = min(sma_periods)
                long_period = sma_periods[1]  # Second shortest period
                
                if df[f'SMA{short_period}'].iloc[-1] > df[f'SMA{long_period}'].iloc[-1]:
                    signals['trend'] = 1  # Bullish trend
                elif df[f'SMA{short_period}'].iloc[-1] < df[f'SMA{long_period}'].iloc[-1]:
                    signals['trend'] = -1  # Bearish trend
            
        # Momentum analysis using RSI and MACD
        if tech_config.get('use_rsi', True):
            rsi_period = tech_config.get('rsi_period', 14)
            # RSI analysis
            if df['RSI'].iloc[-1] < 30:
                signals['momentum'] += 1  # Oversold, bullish signal
            elif df['RSI'].iloc[-1] > 70:
                signals['momentum'] -= 1  # Overbought, bearish signal
            
        if tech_config.get('use_macd', True):
            # MACD analysis
            if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1]:
                signals['momentum'] += 1  # Bullish momentum
            elif df['MACD'].iloc[-1] < df['MACD_Signal'].iloc[-1]:
                signals['momentum'] -= 1  # Bearish momentum
            
        # Volatility analysis using Bollinger Bands
        if tech_config.get('use_bollinger', True):
            bb_width = (df['BB_Upper'].iloc[-1] - df['BB_Lower'].iloc[-1]) / df['BB_Middle'].iloc[-1]
            bb_width_prev = (df['BB_Upper'].iloc[-2] - df['BB_Lower'].iloc[-2]) / df['BB_Middle'].iloc[-2]
            
            # Check if volatility is expanding or contracting
            if bb_width > bb_width_prev:
                signals['volatility'] = 1  # Expanding volatility
            else:
                signals['volatility'] = -1  # Contracting volatility
            
        # Combine signals to determine overall market direction
        trend_weight = signal_config.get('trend_weight', 0.4)
        momentum_weight = signal_config.get('momentum_weight', 0.3)
        volatility_weight = signal_config.get('volatility_weight', 0.3)
        
        weighted_signal = (
            signals['trend'] * trend_weight + 
            signals['momentum'] * momentum_weight + 
            signals['volatility'] * volatility_weight
        )
        
        signal_threshold = signal_config.get('signal_threshold', 0.2)
        
        if weighted_signal > signal_threshold:
            return 'bullish'
        elif weighted_signal < -signal_threshold:
            return 'bearish'
        else:
            return 'neutral'
    
    def _select_options_strategy(self, symbol, signal, current_price, options_data):
        """
        Select appropriate options strategy based on market signal
        
        Args:
            symbol (str): Stock symbol
            signal (str): Market direction signal
            current_price (float): Current stock price
            options_data (dict): Options data for the symbol
            
        Returns:
            dict: Options trading signal with strategy details
        """
        if 'expiry' not in options_data:
            return None
            
        expiry = options_data['expiry']
        
        # Get options strategy configuration
        options_config = self.config.get('options_strategies', {})
        strategy_selection = options_config.get('strategy_selection', {})
        
        # Check if a default strategy is specified
        default_strategy = options_config.get('default_strategy', 'auto')
        if default_strategy != 'auto':
            signal = default_strategy
        
        # Check if Greek optimization is enabled
        use_greeks = self.config.get('use_greek_optimization', True)
        
        # Estimate risk capital (simplified)
        risk_capital = 10000  # Default value
        if 'backtest' in self.config:
            initial_capital = self.config['backtest'].get('initial_capital', 100000)
            risk_per_trade = self.config.get('general', {}).get('risk_per_trade', 0.02)
            risk_capital = initial_capital * risk_per_trade
        
        # Use Greek optimization if enabled and Greeks are available
        if use_greeks and 'calls' in options_data and 'puts' in options_data:
            # Check if Greeks are available in the data
            calls = options_data.get('calls', pd.DataFrame())
            puts = options_data.get('puts', pd.DataFrame())
            
            has_greeks = False
            if not calls.empty and 'delta' in calls.columns:
                has_greeks = True
            
            if has_greeks:
                logger.info(f"Using Greek optimization for {symbol}")
                
                if signal == 'bullish':
                    # Optimize a bullish directional trade
                    optimized_trade = self.greek_optimizer.optimize_directional_trade(
                        options_data, 'bullish', risk_capital
                    )
                    
                    if optimized_trade:
                        # Convert to our standard signal format
                        return {
                            'signal': 'BULLISH',
                            'strategy': optimized_trade['strategy'].upper(),
                            'option': {
                                'strike': optimized_trade['strike'],
                                'lastPrice': optimized_trade['price'],
                                'delta': optimized_trade['delta'],
                                'gamma': optimized_trade['gamma'],
                                'theta': optimized_trade['theta'],
                                'vega': optimized_trade['vega']
                            },
                            'expiry': expiry,
                            'current_price': current_price,
                            'contracts': optimized_trade['contracts'],
                            'greek_optimized': True
                        }
                
                elif signal == 'bearish':
                    # Optimize a bearish directional trade
                    optimized_trade = self.greek_optimizer.optimize_directional_trade(
                        options_data, 'bearish', risk_capital
                    )
                    
                    if optimized_trade:
                        # Convert to our standard signal format
                        return {
                            'signal': 'BEARISH',
                            'strategy': optimized_trade['strategy'].upper(),
                            'option': {
                                'strike': optimized_trade['strike'],
                                'lastPrice': optimized_trade['price'],
                                'delta': optimized_trade['delta'],
                                'gamma': optimized_trade['gamma'],
                                'theta': optimized_trade['theta'],
                                'vega': optimized_trade['vega']
                            },
                            'expiry': expiry,
                            'current_price': current_price,
                            'contracts': optimized_trade['contracts'],
                            'greek_optimized': True
                        }
                
                else:  # neutral
                    # For neutral outlook, optimize a volatility or theta trade
                    # First check if we have a volatility bias
                    volatility_bias = self.config.get('volatility_bias', 'neutral')
                    
                    if volatility_bias == 'increasing':
                        # Optimize for increasing volatility
                        optimized_trade = self.greek_optimizer.optimize_volatility_trade(
                            options_data, 'increasing', risk_capital
                        )
                    elif volatility_bias == 'decreasing':
                        # Optimize for decreasing volatility
                        optimized_trade = self.greek_optimizer.optimize_volatility_trade(
                            options_data, 'decreasing', risk_capital
                        )
                    else:
                        # Default to theta decay trade
                        optimized_trade = self.greek_optimizer.optimize_theta_decay_trade(
                            options_data, risk_capital
                        )
                    
                    if optimized_trade:
                        # Convert to our standard signal format
                        if optimized_trade['strategy'] == 'iron_condor':
                            return {
                                'signal': 'NEUTRAL',
                                'strategy': 'IRON_CONDOR',
                                'sell_call': {
                                    'strike': optimized_trade['short_call_strike'],
                                    'delta': optimized_trade.get('short_call_delta')
                                },
                                'buy_call': {
                                    'strike': optimized_trade['long_call_strike']
                                },
                                'sell_put': {
                                    'strike': optimized_trade['short_put_strike'],
                                    'delta': optimized_trade.get('short_put_delta')
                                },
                                'buy_put': {
                                    'strike': optimized_trade['long_put_strike']
                                },
                                'expiry': expiry,
                                'current_price': current_price,
                                'contracts': optimized_trade['contracts'],
                                'net_credit': optimized_trade['net_credit'],
                                'max_risk': optimized_trade['max_risk'],
                                'total_vega': optimized_trade.get('total_vega'),
                                'greek_optimized': True
                            }
                        elif optimized_trade['strategy'] == 'long_straddle':
                            return {
                                'signal': 'NEUTRAL',
                                'strategy': 'LONG_STRADDLE',
                                'call_strike': optimized_trade['call_strike'],
                                'put_strike': optimized_trade['put_strike'],
                                'expiry': expiry,
                                'current_price': current_price,
                                'contracts': optimized_trade['contracts'],
                                'call_price': optimized_trade['call_price'],
                                'put_price': optimized_trade['put_price'],
                                'total_price': optimized_trade['total_price'],
                                'total_vega': optimized_trade.get('total_vega'),
                                'greek_optimized': True
                            }
                        elif optimized_trade['strategy'] in ['call_credit_spread', 'put_credit_spread']:
                            return {
                                'signal': 'NEUTRAL',
                                'strategy': optimized_trade['strategy'].upper(),
                                'short_strike': optimized_trade['short_strike'],
                                'long_strike': optimized_trade['long_strike'],
                                'expiry': expiry,
                                'current_price': current_price,
                                'contracts': optimized_trade['contracts'],
                                'net_credit': optimized_trade['net_credit'],
                                'max_risk': optimized_trade['max_risk'],
                                'net_theta': optimized_trade.get('net_theta'),
                                'greek_optimized': True
                            }
        
        # Fall back to traditional strategy selection if Greek optimization is disabled or failed
        logger.info(f"Using traditional strategy selection for {symbol}")
        
        # Find ATM options
        calls = options_data.get('calls', pd.DataFrame())
        puts = options_data.get('puts', pd.DataFrame())
        
        if calls.empty or puts.empty:
            return None
            
        # Find closest strike to current price
        calls['strike_diff'] = abs(calls['strike'] - current_price)
        puts['strike_diff'] = abs(puts['strike'] - current_price)
        
        atm_call = calls.loc[calls['strike_diff'].idxmin()]
        atm_put = puts.loc[puts['strike_diff'].idxmin()]
        
        # Get strike selection parameters
        strike_config = options_config.get('strike_selection', {})
        call_itm_pct = strike_config.get('call_itm_pct', 0.03)
        call_otm_pct = strike_config.get('call_otm_pct', 0.05)
        put_itm_pct = strike_config.get('put_itm_pct', 0.03)
        put_otm_pct = strike_config.get('put_otm_pct', 0.05)
        
        # Find slightly OTM options
        otm_call_strike = current_price * (1 + call_otm_pct)
        otm_put_strike = current_price * (1 - put_otm_pct)
        
        calls['otm_diff'] = abs(calls['strike'] - otm_call_strike)
        puts['otm_diff'] = abs(puts['strike'] - otm_put_strike)
        
        otm_call = calls.loc[calls['otm_diff'].idxmin()]
        otm_put = puts.loc[puts['otm_diff'].idxmin()]
        
        # Get IV threshold from config
        iv_threshold = 0.5  # Default
        
        if signal == 'bullish':
            bullish_config = strategy_selection.get('bullish', {})
            iv_threshold = bullish_config.get('iv_threshold', 0.5)
            iv = atm_call['impliedVolatility']
            
            if iv > iv_threshold:  # High IV environment
                strategy_name = bullish_config.get('high_iv', 'bull_put_spread')
                if strategy_name == 'bull_put_spread':
                    return {
                        'signal': 'BULLISH',
                        'strategy': 'BULL_PUT_SPREAD',
                        'sell_option': atm_put,
                        'buy_option': otm_put,
                        'expiry': expiry,
                        'current_price': current_price,
                        'iv': iv,
                        'greek_optimized': False
                    }
            else:  # Low IV environment
                strategy_name = bullish_config.get('low_iv', 'long_call')
                if strategy_name == 'long_call':
                    return {
                        'signal': 'BULLISH',
                        'strategy': 'LONG_CALL',
                        'option': atm_call,
                        'expiry': expiry,
                        'current_price': current_price,
                        'iv': iv,
                        'greek_optimized': False
                    }
                
        elif signal == 'bearish':
            bearish_config = strategy_selection.get('bearish', {})
            iv_threshold = bearish_config.get('iv_threshold', 0.5)
            iv = atm_put['impliedVolatility']
            
            if iv > iv_threshold:  # High IV environment
                strategy_name = bearish_config.get('high_iv', 'bear_call_spread')
                if strategy_name == 'bear_call_spread':
                    return {
                        'signal': 'BEARISH',
                        'strategy': 'BEAR_CALL_SPREAD',
                        'sell_option': atm_call,
                        'buy_option': otm_call,
                        'expiry': expiry,
                        'current_price': current_price,
                        'iv': iv,
                        'greek_optimized': False
                    }
            else:  # Low IV environment
                strategy_name = bearish_config.get('low_iv', 'long_put')
                if strategy_name == 'long_put':
                    return {
                        'signal': 'BEARISH',
                        'strategy': 'LONG_PUT',
                        'option': atm_put,
                        'expiry': expiry,
                        'current_price': current_price,
                        'iv': iv,
                        'greek_optimized': False
                    }
                
        else:  # Neutral
            neutral_config = strategy_selection.get('neutral', {})
            strategy_name = neutral_config.get('default', 'iron_condor')
            iv = (atm_call['impliedVolatility'] + atm_put['impliedVolatility']) / 2
            
            if strategy_name == 'iron_condor':
                return {
                    'signal': 'NEUTRAL',
                    'strategy': 'IRON_CONDOR',
                    'sell_call': otm_call,
                    'sell_put': otm_put,
                    'buy_call': calls.loc[calls['strike'] > otm_call['strike']].iloc[0] if not calls[calls['strike'] > otm_call['strike']].empty else None,
                    'buy_put': puts.loc[puts['strike'] < otm_put['strike']].iloc[0] if not puts[puts['strike'] < otm_put['strike']].empty else None,
                    'expiry': expiry,
                    'current_price': current_price,
                    'iv': iv,
                    'greek_optimized': False
                }
        
        # If we get here, use a default strategy
        iv = (atm_call['impliedVolatility'] + atm_put['impliedVolatility']) / 2
        return {
            'signal': signal.upper(),
            'strategy': 'DEFAULT',
            'call': atm_call,
            'put': atm_put,
            'expiry': expiry,
            'current_price': current_price,
            'iv': iv,
            'greek_optimized': False
        }
    
    def calculate_expected_profit(self, option_signal):
        """
        Calculate expected profit and risk for an options strategy
        
        Args:
            option_signal (dict): Options trading signal
            
        Returns:
            dict: Dictionary with profit and risk metrics
        """
        strategy = option_signal.get('strategy')
        
        if strategy == 'LONG_CALL':
            option = option_signal['option']
            premium = option['lastPrice']
            strike = option['strike']
            current_price = option_signal['current_price']
            
            max_loss = premium
            max_profit = 'Unlimited'
            breakeven = strike + premium
            
            return {
                'max_loss': max_loss,
                'max_profit': max_profit,
                'breakeven': breakeven
            }
            
        elif strategy == 'LONG_PUT':
            option = option_signal['option']
            premium = option['lastPrice']
            strike = option['strike']
            current_price = option_signal['current_price']
            
            max_loss = premium
            max_profit = strike - premium
            breakeven = strike - premium
            
            return {
                'max_loss': max_loss,
                'max_profit': max_profit,
                'breakeven': breakeven
            }
            
        elif strategy == 'BULL_PUT_SPREAD':
            sell_option = option_signal['sell_option']
            buy_option = option_signal['buy_option']
            
            sell_premium = sell_option['lastPrice']
            buy_premium = buy_option['lastPrice']
            sell_strike = sell_option['strike']
            buy_strike = buy_option['strike']
            
            net_credit = sell_premium - buy_premium
            max_loss = (sell_strike - buy_strike) - net_credit
            max_profit = net_credit
            breakeven = sell_strike - net_credit
            
            return {
                'max_loss': max_loss,
                'max_profit': max_profit,
                'breakeven': breakeven
            }
            
        elif strategy == 'BEAR_CALL_SPREAD':
            sell_option = option_signal['sell_option']
            buy_option = option_signal['buy_option']
            
            sell_premium = sell_option['lastPrice']
            buy_premium = buy_option['lastPrice']
            sell_strike = sell_option['strike']
            buy_strike = buy_option['strike']
            
            net_credit = sell_premium - buy_premium
            max_loss = (buy_strike - sell_strike) - net_credit
            max_profit = net_credit
            breakeven = sell_strike + net_credit
            
            return {
                'max_loss': max_loss,
                'max_profit': max_profit,
                'breakeven': breakeven
            }
            
        elif strategy == 'IRON_CONDOR':
            sell_call = option_signal['sell_call']
            sell_put = option_signal['sell_put']
            buy_call = option_signal['buy_call']
            buy_put = option_signal['buy_put']
            
            if buy_call is None or buy_put is None:
                return None
                
            sell_call_premium = sell_call['lastPrice']
            sell_put_premium = sell_put['lastPrice']
            buy_call_premium = buy_call['lastPrice']
            buy_put_premium = buy_put['lastPrice']
            
            sell_call_strike = sell_call['strike']
            sell_put_strike = sell_put['strike']
            buy_call_strike = buy_call['strike']
            buy_put_strike = buy_put['strike']
            
            net_credit = (sell_call_premium + sell_put_premium) - (buy_call_premium + buy_put_premium)
            max_loss = min((buy_call_strike - sell_call_strike), (sell_put_strike - buy_put_strike)) - net_credit
            max_profit = net_credit
            
            return {
                'max_loss': max_loss,
                'max_profit': max_profit,
                'breakeven_upper': sell_call_strike + net_credit,
                'breakeven_lower': sell_put_strike - net_credit
            }
            
        return None
