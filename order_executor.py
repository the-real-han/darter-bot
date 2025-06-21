#!/usr/bin/env python3
"""
Order Executor Module
------------------
Handles order execution for the trading bot
"""

import os
import logging
import json
from datetime import datetime
from trading_platforms.platform_factory import TradingPlatformFactory
from trading_platforms.base_platform import OrderType, OrderSide, OrderStatus

logger = logging.getLogger('trading_bot.order_executor')

class OrderExecutor:
    def __init__(self, platform_name='paper', config_path=None, output_dir=None, username=None, password=None, auth_token=None, **kwargs):
        """
        Initialize the order executor
        
        Args:
            platform_name (str): Name of the trading platform
            config_path (str): Path to configuration file
            output_dir (str): Directory to save output files
            username (str): Username for the trading platform (legacy)
            password (str): Password for the trading platform (legacy)
            auth_token (str): Authentication bearer token for trading platform
            **kwargs: Additional platform-specific parameters
        """
        self.platform_name = platform_name
        self.config_path = config_path
        self.output_dir = output_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        self.username = username
        self.password = password
        self.auth_token = auth_token
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize trading platform
        self.platform = TradingPlatformFactory.get_platform(
            platform_name, 
            username=self.username, 
            password=self.password,
            auth_token=self.auth_token,
            **kwargs
        )
        
        # Authenticate with platform
        if not self.platform.authenticated:
            success = self.platform.authenticate()
            if not success:
                logger.error(f"Failed to authenticate with {platform_name} platform")
        
        logger.info(f"Order executor initialized with {platform_name} platform")
    
    def _load_config(self):
        """
        Load configuration from file
        
        Returns:
            dict: Configuration
        """
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        
        # Default configuration
        return {
            'max_positions': 5,
            'position_size': 0.1,  # 10% of account per position
            'enable_options': True,
            'enable_stocks': True
        }
    
    def get_account_info(self):
        """
        Get account information
        
        Returns:
            dict: Account information
        """
        return self.platform.get_account_info()
    
    def get_positions(self):
        """
        Get current positions
        
        Returns:
            list: List of positions
        """
        return self.platform.get_positions()
    
    def execute_option_signal(self, signal):
        """
        Execute an options trading signal
        
        Args:
            signal (dict): Options trading signal
            
        Returns:
            dict: Order information
        """
        if not self.config.get('enable_options', True):
            logger.info("Options trading is disabled in configuration")
            return None
        
        try:
            # Extract signal information
            symbol = signal['symbol']
            strategy = signal['strategy']
            
            # Get account information
            account_info = self.platform.get_account_info()
            buying_power = account_info.get('buying_power', 0)
            
            # Check if we have enough buying power
            if buying_power <= 0:
                logger.warning(f"Insufficient buying power: {buying_power}")
                return None
            
            # Calculate position size
            position_size = buying_power * self.config.get('position_size', 0.1)
            
            # Check if we already have too many positions
            current_positions = self.platform.get_positions()
            max_positions = self.config.get('max_positions', 5)
            
            if len(current_positions) >= max_positions:
                logger.warning(f"Maximum positions reached: {len(current_positions)}/{max_positions}")
                return None
            
            # Execute order based on strategy
            if strategy == 'LONG_CALL':
                # Extract option information
                option = signal['option']
                expiry = signal['expiry']
                strike = option['strike']
                option_price = option['lastPrice']
                
                # Calculate quantity (contracts)
                quantity = max(1, int(position_size / (option_price * 100)))
                
                # Place order
                order = self.platform.place_option_order(
                    symbol=symbol,
                    expiry=expiry,
                    strike=strike,
                    option_type='call',
                    quantity=quantity,
                    side=OrderSide.BUY_TO_OPEN,
                    order_type=OrderType.MARKET
                )
                
                logger.info(f"Executed LONG_CALL signal for {symbol}: {quantity} contracts at strike {strike}")
                return order
                
            elif strategy == 'LONG_PUT':
                # Extract option information
                option = signal['option']
                expiry = signal['expiry']
                strike = option['strike']
                option_price = option['lastPrice']
                
                # Calculate quantity (contracts)
                quantity = max(1, int(position_size / (option_price * 100)))
                
                # Place order
                order = self.platform.place_option_order(
                    symbol=symbol,
                    expiry=expiry,
                    strike=strike,
                    option_type='put',
                    quantity=quantity,
                    side=OrderSide.BUY_TO_OPEN,
                    order_type=OrderType.MARKET
                )
                
                logger.info(f"Executed LONG_PUT signal for {symbol}: {quantity} contracts at strike {strike}")
                return order
                
            elif strategy == 'BULL_PUT_SPREAD':
                # Extract option information
                sell_option = signal['sell_option']
                buy_option = signal['buy_option']
                expiry = signal['expiry']
                
                sell_strike = sell_option['strike']
                buy_strike = buy_option['strike']
                
                # Calculate max risk per contract
                max_risk = (sell_strike - buy_strike) * 100
                
                # Calculate quantity (contracts)
                quantity = max(1, int(position_size / max_risk))
                
                # Place sell put order
                sell_order = self.platform.place_option_order(
                    symbol=symbol,
                    expiry=expiry,
                    strike=sell_strike,
                    option_type='put',
                    quantity=quantity,
                    side=OrderSide.SELL_TO_OPEN,
                    order_type=OrderType.MARKET
                )
                
                # Place buy put order
                buy_order = self.platform.place_option_order(
                    symbol=symbol,
                    expiry=expiry,
                    strike=buy_strike,
                    option_type='put',
                    quantity=quantity,
                    side=OrderSide.BUY_TO_OPEN,
                    order_type=OrderType.MARKET
                )
                
                logger.info(f"Executed BULL_PUT_SPREAD signal for {symbol}: {quantity} contracts")
                return {
                    'strategy': 'BULL_PUT_SPREAD',
                    'sell_order': sell_order,
                    'buy_order': buy_order
                }
                
            elif strategy == 'BEAR_CALL_SPREAD':
                # Extract option information
                sell_option = signal['sell_option']
                buy_option = signal['buy_option']
                expiry = signal['expiry']
                
                sell_strike = sell_option['strike']
                buy_strike = buy_option['strike']
                
                # Calculate max risk per contract
                max_risk = (buy_strike - sell_strike) * 100
                
                # Calculate quantity (contracts)
                quantity = max(1, int(position_size / max_risk))
                
                # Place sell call order
                sell_order = self.platform.place_option_order(
                    symbol=symbol,
                    expiry=expiry,
                    strike=sell_strike,
                    option_type='call',
                    quantity=quantity,
                    side=OrderSide.SELL_TO_OPEN,
                    order_type=OrderType.MARKET
                )
                
                # Place buy call order
                buy_order = self.platform.place_option_order(
                    symbol=symbol,
                    expiry=expiry,
                    strike=buy_strike,
                    option_type='call',
                    quantity=quantity,
                    side=OrderSide.BUY_TO_OPEN,
                    order_type=OrderType.MARKET
                )
                
                logger.info(f"Executed BEAR_CALL_SPREAD signal for {symbol}: {quantity} contracts")
                return {
                    'strategy': 'BEAR_CALL_SPREAD',
                    'sell_order': sell_order,
                    'buy_order': buy_order
                }
                
            elif strategy == 'IRON_CONDOR':
                # Extract option information
                sell_call = signal['sell_call']
                buy_call = signal['buy_call']
                sell_put = signal['sell_put']
                buy_put = signal['buy_put']
                expiry = signal['expiry']
                
                # Check if we have all the required options
                if not buy_call or not buy_put:
                    logger.warning(f"Missing options for IRON_CONDOR strategy")
                    return None
                
                # Calculate max risk per contract
                call_spread_width = buy_call['strike'] - sell_call['strike']
                put_spread_width = sell_put['strike'] - buy_put['strike']
                max_risk = max(call_spread_width, put_spread_width) * 100
                
                # Calculate quantity (contracts)
                quantity = max(1, int(position_size / max_risk))
                
                # Place orders
                orders = {
                    'strategy': 'IRON_CONDOR',
                    'sell_call_order': self.platform.place_option_order(
                        symbol=symbol,
                        expiry=expiry,
                        strike=sell_call['strike'],
                        option_type='call',
                        quantity=quantity,
                        side=OrderSide.SELL_TO_OPEN,
                        order_type=OrderType.MARKET
                    ),
                    'buy_call_order': self.platform.place_option_order(
                        symbol=symbol,
                        expiry=expiry,
                        strike=buy_call['strike'],
                        option_type='call',
                        quantity=quantity,
                        side=OrderSide.BUY_TO_OPEN,
                        order_type=OrderType.MARKET
                    ),
                    'sell_put_order': self.platform.place_option_order(
                        symbol=symbol,
                        expiry=expiry,
                        strike=sell_put['strike'],
                        option_type='put',
                        quantity=quantity,
                        side=OrderSide.SELL_TO_OPEN,
                        order_type=OrderType.MARKET
                    ),
                    'buy_put_order': self.platform.place_option_order(
                        symbol=symbol,
                        expiry=expiry,
                        strike=buy_put['strike'],
                        option_type='put',
                        quantity=quantity,
                        side=OrderSide.BUY_TO_OPEN,
                        order_type=OrderType.MARKET
                    )
                }
                
                logger.info(f"Executed IRON_CONDOR signal for {symbol}: {quantity} contracts")
                return orders
            
            else:
                logger.warning(f"Unsupported strategy: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing options signal: {e}")
            return None
    
    def close_position(self, position):
        """
        Close a position
        
        Args:
            position (dict): Position to close
            
        Returns:
            dict: Order information
        """
        try:
            asset_type = position.get('asset_type')
            
            if asset_type == 'stock':
                # Close stock position
                symbol = position['symbol']
                quantity = position['quantity']
                
                order = self.platform.place_stock_order(
                    symbol=symbol,
                    quantity=quantity,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET
                )
                
                logger.info(f"Closed stock position for {symbol}: {quantity} shares")
                return order
                
            elif asset_type == 'option':
                # Close option position
                symbol = position['symbol']
                option_symbol = position.get('option_symbol')
                expiry = position['expiry']
                strike = position['strike']
                option_type = position['option_type']
                quantity = position['quantity']
                position_type = position.get('position_type', 'long')
                
                if position_type == 'long':
                    side = OrderSide.SELL_TO_CLOSE
                else:
                    side = OrderSide.BUY_TO_CLOSE
                
                order = self.platform.place_option_order(
                    symbol=symbol,
                    expiry=expiry,
                    strike=strike,
                    option_type=option_type,
                    quantity=quantity,
                    side=side,
                    order_type=OrderType.MARKET
                )
                
                logger.info(f"Closed option position for {option_symbol}: {quantity} contracts")
                return order
                
            else:
                logger.warning(f"Unsupported asset type: {asset_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
    
    def save_execution_log(self, signal, order):
        """
        Save execution log to file
        
        Args:
            signal (dict): Trading signal
            order (dict): Order information
        """
        try:
            log_file = os.path.join(self.output_dir, 'execution_log.json')
            
            # Load existing log or create new one
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log = json.load(f)
            else:
                log = []
            
            # Add new entry
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'signal': {
                    'symbol': signal.get('symbol'),
                    'strategy': signal.get('strategy')
                },
                'order': order,
                'platform': self.platform_name
            }
            
            log.append(log_entry)
            
            # Save log
            with open(log_file, 'w') as f:
                json.dump(log, f, indent=4)
                
            logger.info(f"Saved execution log to {log_file}")
            
        except Exception as e:
            logger.error(f"Error saving execution log: {e}")
    
    def process_signals(self, signals):
        """
        Process trading signals and execute orders
        
        Args:
            signals (dict): Dictionary of trading signals
            
        Returns:
            dict: Dictionary of executed orders
        """
        executed_orders = {}
        
        for symbol, signal in signals.items():
            try:
                # Execute signal
                order = self.execute_option_signal(signal)
                
                if order:
                    executed_orders[symbol] = order
                    self.save_execution_log(signal, order)
                
            except Exception as e:
                logger.error(f"Error processing signal for {symbol}: {e}")
        
        return executed_orders
