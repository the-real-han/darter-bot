#!/usr/bin/env python3
"""
Options Backtest Module for Trading Bot
-------------------------------------
Implements backtesting functionality for options trading strategies
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('trading_bot.options_backtest')

class OptionsBacktest:
    def __init__(self):
        """Initialize the options backtest handler"""
        pass
    
    def run(self, signals, options_signals, initial_capital=100000, config=None):
        """
        Run backtest on the options trading signals
        
        Args:
            signals (dict): Dictionary of DataFrames with stock signal columns
            options_signals (dict): Dictionary of options trading signals
            initial_capital (float): Initial capital for backtesting
            config (dict): Strategy configuration
            
        Returns:
            dict: Dictionary of performance metrics for each symbol
        """
        results = {}
        
        # Use default config if none provided
        if config is None:
            from strategy_config import load_strategy_config
            config = load_strategy_config()
        
        # Get stop loss and take profit settings
        options_config = config.get('options_strategies', {})
        stop_loss_pct = options_config.get('stop_loss_pct', 0.5)  # Default 50% stop loss
        take_profit_pct = options_config.get('take_profit_pct', 1.0)  # Default 100% take profit
        max_days_to_hold = options_config.get('max_days_to_hold', 14)  # Default 14 days max hold
        
        for symbol, df in signals.items():
            if df is None or df.empty or 'Signal' not in df.columns:
                continue
                
            if symbol not in options_signals:
                continue
                
            df_copy = df.copy()
            
            # Initialize portfolio columns
            df_copy['Position'] = 0
            df_copy['Cash'] = initial_capital
            df_copy['Holdings'] = 0
            df_copy['Portfolio'] = initial_capital
            df_copy['Stop_Loss'] = 0
            df_copy['Take_Profit'] = 0
            df_copy['Days_Held'] = 0
            df_copy['Exit_Reason'] = None
            
            # Get options signal
            option_signal = options_signals[symbol]
            strategy = option_signal.get('strategy')
            
            # Simulate options trading based on strategy
            position = 0
            entry_price = 0
            entry_date = None
            stop_loss_price = 0
            take_profit_price = 0
            
            for i in range(1, len(df_copy)):
                current_date = df_copy.index[i]
                
                # Update days held if in a position
                if position > 0:
                    days_held = (current_date - entry_date).days
                    df_copy.loc[current_date, 'Days_Held'] = days_held
                
                # Check for exit conditions if in a position
                if position > 0:
                    # Calculate current option value
                    if strategy in ['LONG_CALL', 'LONG_PUT']:
                        days_held = (current_date - entry_date).days
                        time_decay = min(0.1 * days_held, 0.5)  # Simplified time decay
                        
                        if strategy == 'LONG_CALL':
                            intrinsic_value = max(0, df_copy['Close'].iloc[i] - option_signal['option']['strike'])
                        else:  # LONG_PUT
                            intrinsic_value = max(0, option_signal['option']['strike'] - df_copy['Close'].iloc[i])
                            
                        option_value = max(intrinsic_value, option_signal['option']['lastPrice'] * (1 - time_decay))
                        current_value = position * option_value * 100
                        
                        # Check stop loss
                        if option_value <= stop_loss_price:
                            df_copy.loc[current_date, 'Cash'] = df_copy['Cash'].iloc[i-1] + current_value
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Stop Loss'
                            position = 0
                            logger.info(f"Stop loss triggered for {symbol} at {current_date}")
                            
                        # Check take profit
                        elif option_value >= take_profit_price:
                            df_copy.loc[current_date, 'Cash'] = df_copy['Cash'].iloc[i-1] + current_value
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Take Profit'
                            position = 0
                            logger.info(f"Take profit triggered for {symbol} at {current_date}")
                            
                        # Check max days to hold
                        elif days_held >= max_days_to_hold:
                            df_copy.loc[current_date, 'Cash'] = df_copy['Cash'].iloc[i-1] + current_value
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Max Days'
                            position = 0
                            logger.info(f"Max days held reached for {symbol} at {current_date}")
                            
                        # Check for signal reversal
                        elif (strategy == 'LONG_CALL' and df_copy['Signal'].iloc[i-1] == -1) or \
                             (strategy == 'LONG_PUT' and df_copy['Signal'].iloc[i-1] == 1):
                            df_copy.loc[current_date, 'Cash'] = df_copy['Cash'].iloc[i-1] + current_value
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Signal Reversal'
                            position = 0
                            logger.info(f"Signal reversal exit for {symbol} at {current_date}")
                            
                        else:
                            # Continue holding
                            df_copy.loc[current_date, 'Cash'] = df_copy['Cash'].iloc[i-1]
                            df_copy.loc[current_date, 'Holdings'] = current_value
                    
                    elif strategy in ['BULL_PUT_SPREAD', 'BEAR_CALL_SPREAD']:
                        # Simplified model for credit spreads
                        days_held = (current_date - entry_date).days
                        
                        # For credit spreads, check if we can exit early for a percentage of max profit
                        credit_received = df_copy['Cash'].iloc[i-1] - initial_capital
                        
                        # Calculate approximate current value (simplified)
                        time_factor = 1 - (days_held / 30)  # Assume 30 days to expiration
                        if time_factor < 0:
                            time_factor = 0
                            
                        # For credit spreads, profit increases as time passes
                        profit_pct = 1 - time_factor
                        
                        # Check take profit (e.g., 70% of max credit)
                        if profit_pct >= 0.7:
                            df_copy.loc[current_date, 'Cash'] = initial_capital + (credit_received * 0.7)
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Take Profit'
                            position = 0
                            logger.info(f"Take profit triggered for {symbol} credit spread at {current_date}")
                            
                        # Check max days to hold
                        elif days_held >= max_days_to_hold:
                            df_copy.loc[current_date, 'Cash'] = initial_capital + (credit_received * profit_pct)
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Max Days'
                            position = 0
                            logger.info(f"Max days held reached for {symbol} credit spread at {current_date}")
                            
                        # Check for signal reversal
                        elif (strategy == 'BULL_PUT_SPREAD' and df_copy['Signal'].iloc[i-1] == -1) or \
                             (strategy == 'BEAR_CALL_SPREAD' and df_copy['Signal'].iloc[i-1] == 1):
                            df_copy.loc[current_date, 'Cash'] = initial_capital + (credit_received * profit_pct)
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Signal Reversal'
                            position = 0
                            logger.info(f"Signal reversal exit for {symbol} credit spread at {current_date}")
                            
                        else:
                            # Continue holding
                            df_copy.loc[current_date, 'Cash'] = df_copy['Cash'].iloc[i-1]
                            df_copy.loc[current_date, 'Holdings'] = df_copy['Holdings'].iloc[i-1]
                    
                    elif strategy == 'IRON_CONDOR':
                        # Similar logic to credit spreads
                        days_held = (current_date - entry_date).days
                        credit_received = df_copy['Cash'].iloc[i-1] - initial_capital
                        
                        # Calculate approximate current value (simplified)
                        time_factor = 1 - (days_held / 30)  # Assume 30 days to expiration
                        if time_factor < 0:
                            time_factor = 0
                            
                        profit_pct = 1 - time_factor
                        
                        # Check take profit (e.g., 60% of max credit)
                        if profit_pct >= 0.6:
                            df_copy.loc[current_date, 'Cash'] = initial_capital + (credit_received * 0.6)
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Take Profit'
                            position = 0
                            logger.info(f"Take profit triggered for {symbol} iron condor at {current_date}")
                            
                        # Check max days to hold
                        elif days_held >= max_days_to_hold:
                            df_copy.loc[current_date, 'Cash'] = initial_capital + (credit_received * profit_pct)
                            df_copy.loc[current_date, 'Holdings'] = 0
                            df_copy.loc[current_date, 'Exit_Reason'] = 'Max Days'
                            position = 0
                            logger.info(f"Max days held reached for {symbol} iron condor at {current_date}")
                            
                        else:
                            # Continue holding
                            df_copy.loc[current_date, 'Cash'] = df_copy['Cash'].iloc[i-1]
                            df_copy.loc[current_date, 'Holdings'] = df_copy['Holdings'].iloc[i-1]
                
                # Check for entry conditions if not in a position
                elif df_copy['Signal'].iloc[i-1] == 1 and position == 0:  # Buy signal
                    # Simulate options purchase
                    if strategy in ['LONG_CALL', 'LONG_PUT']:
                        option_price = option_signal['option']['lastPrice']
                        contracts = int(initial_capital / (option_price * 100))  # Each contract is for 100 shares
                        cost = contracts * option_price * 100
                        
                        # Set stop loss and take profit levels
                        stop_loss_price = option_price * (1 - stop_loss_pct)
                        take_profit_price = option_price * (1 + take_profit_pct)
                        
                        df_copy.loc[current_date, 'Cash'] = initial_capital - cost
                        df_copy.loc[current_date, 'Holdings'] = cost
                        df_copy.loc[current_date, 'Stop_Loss'] = stop_loss_price
                        df_copy.loc[current_date, 'Take_Profit'] = take_profit_price
                        position = contracts
                        entry_date = current_date
                        
                    elif strategy in ['BULL_PUT_SPREAD', 'BEAR_CALL_SPREAD']:
                        sell_option = option_signal['sell_option']
                        buy_option = option_signal['buy_option']
                        
                        sell_premium = sell_option['lastPrice']
                        buy_premium = buy_option['lastPrice']
                        net_credit = sell_premium - buy_premium
                        
                        contracts = int(initial_capital / ((sell_option['strike'] - buy_option['strike']) * 100))
                        credit_received = contracts * net_credit * 100
                        
                        df_copy.loc[current_date, 'Cash'] = initial_capital + credit_received
                        df_copy.loc[current_date, 'Holdings'] = 0  # Credit spread starts with no holdings value
                        position = contracts
                        entry_date = current_date
                        
                    elif strategy == 'IRON_CONDOR':
                        sell_call = option_signal['sell_call']
                        sell_put = option_signal['sell_put']
                        buy_call = option_signal['buy_call']
                        buy_put = option_signal['buy_put']
                        
                        if buy_call is None or buy_put is None:
                            continue
                            
                        sell_call_premium = sell_call['lastPrice']
                        sell_put_premium = sell_put['lastPrice']
                        buy_call_premium = buy_call['lastPrice']
                        buy_put_premium = buy_put['lastPrice']
                        
                        net_credit = (sell_call_premium + sell_put_premium) - (buy_call_premium + buy_put_premium)
                        
                        # Calculate max risk (width of the wider spread)
                        call_spread_width = buy_call['strike'] - sell_call['strike']
                        put_spread_width = sell_put['strike'] - buy_put['strike']
                        max_risk = max(call_spread_width, put_spread_width) - net_credit
                        
                        contracts = int(initial_capital / (max_risk * 100))
                        credit_received = contracts * net_credit * 100
                        
                        df_copy.loc[current_date, 'Cash'] = initial_capital + credit_received
                        df_copy.loc[current_date, 'Holdings'] = 0
                        position = contracts
                        entry_date = current_date
                
                # Update portfolio value
                if current_date not in df_copy.index:
                    continue
                    
                df_copy.loc[current_date, 'Position'] = position
                df_copy.loc[current_date, 'Portfolio'] = df_copy.loc[current_date, 'Cash'] + df_copy.loc[current_date, 'Holdings']
            
            # Calculate performance metrics
            df_copy['Returns'] = df_copy['Portfolio'].pct_change()
            
            results[symbol] = {
                'Final_Portfolio': df_copy['Portfolio'].iloc[-1],
                'Total_Return': (df_copy['Portfolio'].iloc[-1] / initial_capital - 1) * 100,
                'Max_Drawdown': (df_copy['Portfolio'] / df_copy['Portfolio'].cummax() - 1).min() * 100,
                'Sharpe_Ratio': df_copy['Returns'].mean() / df_copy['Returns'].std() * (252 ** 0.5) if df_copy['Returns'].std() != 0 else 0,
                'Strategy': strategy,
                'Data': df_copy  # Store the DataFrame for further analysis
            }
            
            # Count exit reasons
            exit_reasons = df_copy['Exit_Reason'].value_counts().to_dict()
            results[symbol]['Exit_Reasons'] = exit_reasons
            
            logger.info(f"Options backtest results for {symbol} ({strategy}): Total Return: {results[symbol]['Total_Return']:.2f}%, Max Drawdown: {results[symbol]['Max_Drawdown']:.2f}%")
            if exit_reasons:
                logger.info(f"Exit reasons for {symbol}: {exit_reasons}")
        
        return results
    
    def visualize(self, symbol, results, output_dir=None):
        """
        Visualize options backtest results for a symbol
        
        Args:
            symbol (str): Symbol to visualize
            results (dict): Dictionary of backtest results
            output_dir (str): Directory to save output files
        """
        if symbol not in results:
            logger.error(f"No options backtest results available for {symbol}")
            return
            
        df = results[symbol]['Data']
        strategy = results[symbol]['Strategy']
        
        # Create a figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 16), gridspec_kw={'height_ratios': [2, 1, 1]})
        
        # Plot price and signals
        ax1.plot(df.index, df['Close'], label='Close Price')
        
        # Plot buy/sell signals
        buy_signals = df[df['Signal'] == 1]
        sell_signals = df[df['Signal'] == -1]
        
        ax1.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='g', s=100, label='Buy Signal')
        ax1.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='r', s=100, label='Sell Signal')
        
        # Plot stop loss and take profit levels if available
        if 'Stop_Loss' in df.columns and 'Take_Profit' in df.columns:
            # Find where stop loss and take profit are set (non-zero)
            stop_loss_points = df[df['Stop_Loss'] > 0]
            take_profit_points = df[df['Take_Profit'] > 0]
            
            if not stop_loss_points.empty:
                ax1.scatter(stop_loss_points.index, stop_loss_points['Close'], marker='_', color='r', s=100, label='Stop Loss Set')
            
            if not take_profit_points.empty:
                ax1.scatter(take_profit_points.index, take_profit_points['Close'], marker='_', color='g', s=100, label='Take Profit Set')
        
        # Plot exit reasons if available
        if 'Exit_Reason' in df.columns:
            exit_points = df[df['Exit_Reason'].notnull()]
            
            for reason in exit_points['Exit_Reason'].unique():
                points = exit_points[exit_points['Exit_Reason'] == reason]
                ax1.scatter(points.index, points['Close'], marker='X', s=150, label=f'Exit: {reason}')
        
        ax1.set_title(f'{symbol} Options Strategy: {strategy}')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True)
        
        # Plot portfolio value
        ax2.plot(df.index, df['Portfolio'], label='Portfolio Value')
        ax2.set_ylabel('Portfolio Value')
        ax2.legend()
        ax2.grid(True)
        
        # Plot position and days held
        ax3.plot(df.index, df['Position'], label='Position Size', color='blue')
        
        if 'Days_Held' in df.columns:
            ax3_twin = ax3.twinx()
            ax3_twin.plot(df.index, df['Days_Held'], label='Days Held', color='orange', linestyle='--')
            ax3_twin.set_ylabel('Days Held')
            ax3_twin.legend(loc='upper right')
        
        ax3.set_ylabel('Position Size')
        ax3.set_xlabel('Date')
        ax3.legend(loc='upper left')
        ax3.grid(True)
        
        plt.tight_layout()
        
        # Save the figure
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            save_path = os.path.join(output_dir, f'{symbol}_options_backtest.png')
        else:
            save_path = f'{symbol}_options_backtest.png'
            
        plt.savefig(save_path)
        logger.info(f"Saved options backtest visualization for {symbol} to {save_path}")
        plt.close(fig)
    
    def generate_report(self, results):
        """
        Generate a summary report of options backtest results
        
        Args:
            results (dict): Dictionary of backtest results
            
        Returns:
            DataFrame: Summary of backtest results
        """
        summary = {}
        
        for symbol, metrics in results.items():
            summary[symbol] = {
                'Strategy': metrics['Strategy'],
                'Total Return (%)': metrics['Total_Return'],
                'Max Drawdown (%)': metrics['Max_Drawdown'],
                'Sharpe Ratio': metrics['Sharpe_Ratio'],
                'Final Portfolio Value': metrics['Final_Portfolio']
            }
            
            # Add exit reasons if available
            if 'Exit_Reasons' in metrics:
                for reason, count in metrics['Exit_Reasons'].items():
                    summary[symbol][f'Exit: {reason}'] = count
        
        return pd.DataFrame.from_dict(summary, orient='index')
