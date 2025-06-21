#!/usr/bin/env python3
"""
Paper Trading Platform Module
--------------------------
Implements a simple paper trading platform for simulation
"""

import json
import os
import logging
from datetime import datetime
from .base_platform import BaseTradingPlatform, OrderType, OrderSide, OrderStatus

logger = logging.getLogger('trading_bot.trading_platforms.paper')

class PaperTradingPlatform(BaseTradingPlatform):
    """Paper trading platform implementation for simulation"""
    
    def __init__(self, initial_balance=100000, data_dir=None, **kwargs):
        """
        Initialize the paper trading platform
        
        Args:
            initial_balance (float): Initial account balance
            data_dir (str): Directory to store paper trading data
            **kwargs: Additional parameters
        """
        self.initial_balance = initial_balance
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), '../output/paper_trading')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize platform
        super().__init__(**kwargs)
    
    def initialize_client(self, **kwargs):
        """Initialize the paper trading client"""
        self.client = True  # Dummy client
        self.authenticated = True  # Always authenticated for paper trading
        
        # Load or create account data
        self._load_account_data()
        
        logger.info("Paper trading platform initialized")
    
    def authenticate(self):
        """
        Authenticate with the paper trading platform
        
        Returns:
            bool: Always True for paper trading
        """
        return True
    
    def get_account_info(self):
        """
        Get account information
        
        Returns:
            dict: Account information
        """
        return self.account_data
    
    def get_positions(self):
        """
        Get current positions
        
        Returns:
            list: List of positions
        """
        return self.positions
    
    def get_orders(self, status=None):
        """
        Get orders
        
        Args:
            status (OrderStatus): Filter orders by status
            
        Returns:
            list: List of orders
        """
        if status is None:
            return self.orders
        else:
            return [order for order in self.orders if order['status'] == status]
    
    def place_stock_order(self, symbol, quantity, side, order_type=OrderType.MARKET, price=None, stop_price=None):
        """
        Place a stock order
        
        Args:
            symbol (str): Stock symbol
            quantity (int): Number of shares
            side (OrderSide): Order side (BUY or SELL)
            order_type (OrderType): Order type
            price (float): Limit price (for LIMIT and STOP_LIMIT orders)
            stop_price (float): Stop price (for STOP and STOP_LIMIT orders)
            
        Returns:
            dict: Order information
        """
        # Generate order ID
        order_id = f"paper-{len(self.orders) + 1}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create order
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'side': side.value,
            'order_type': order_type.value,
            'price': price,
            'stop_price': stop_price,
            'status': OrderStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'filled_at': None,
            'filled_price': None,
            'asset_type': 'stock'
        }
        
        # Add order to list
        self.orders.append(order)
        
        # For market orders, execute immediately
        if order_type == OrderType.MARKET:
            self._execute_order(order)
        
        # Save account data
        self._save_account_data()
        
        logger.info(f"Placed {side.value} order for {quantity} shares of {symbol}")
        return order
    
    def place_option_order(self, symbol, expiry, strike, option_type, quantity, side, order_type=OrderType.MARKET, price=None):
        """
        Place an option order
        
        Args:
            symbol (str): Stock symbol
            expiry (str): Option expiration date (YYYY-MM-DD)
            strike (float): Strike price
            option_type (str): Option type ('call' or 'put')
            quantity (int): Number of contracts
            side (OrderSide): Order side
            order_type (OrderType): Order type
            price (float): Limit price (for LIMIT orders)
            
        Returns:
            dict: Order information
        """
        # Generate order ID
        order_id = f"paper-{len(self.orders) + 1}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Format option symbol
        option_symbol = f"{symbol}_{expiry}_{strike}_{option_type}"
        
        # Create order
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'option_symbol': option_symbol,
            'expiry': expiry,
            'strike': strike,
            'option_type': option_type,
            'quantity': quantity,
            'side': side.value,
            'order_type': order_type.value,
            'price': price,
            'status': OrderStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'filled_at': None,
            'filled_price': None,
            'asset_type': 'option'
        }
        
        # Add order to list
        self.orders.append(order)
        
        # For market orders, execute immediately
        if order_type == OrderType.MARKET:
            self._execute_order(order)
        
        # Save account data
        self._save_account_data()
        
        logger.info(f"Placed {side.value} order for {quantity} contracts of {option_symbol}")
        return order
    
    def cancel_order(self, order_id):
        """
        Cancel an order
        
        Args:
            order_id (str): Order ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        for i, order in enumerate(self.orders):
            if order['order_id'] == order_id and order['status'] == OrderStatus.PENDING.value:
                # Update order status
                self.orders[i]['status'] = OrderStatus.CANCELLED.value
                self.orders[i]['updated_at'] = datetime.now().isoformat()
                
                # Save account data
                self._save_account_data()
                
                logger.info(f"Cancelled order {order_id}")
                return True
        
        logger.warning(f"Order {order_id} not found or not pending")
        return False
    
    def get_order_status(self, order_id):
        """
        Get order status
        
        Args:
            order_id (str): Order ID
            
        Returns:
            OrderStatus: Order status
        """
        for order in self.orders:
            if order['order_id'] == order_id:
                return OrderStatus(order['status'])
        
        logger.warning(f"Order {order_id} not found")
        return OrderStatus.REJECTED
    
    def _load_account_data(self):
        """Load account data from file or create new account"""
        account_file = os.path.join(self.data_dir, 'account.json')
        positions_file = os.path.join(self.data_dir, 'positions.json')
        orders_file = os.path.join(self.data_dir, 'orders.json')
        
        # Load account data
        try:
            if os.path.exists(account_file):
                with open(account_file, 'r') as f:
                    self.account_data = json.load(f)
            else:
                self.account_data = {
                    'balance': self.initial_balance,
                    'equity': self.initial_balance,
                    'buying_power': self.initial_balance,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error loading account data: {e}")
            self.account_data = {
                'balance': self.initial_balance,
                'equity': self.initial_balance,
                'buying_power': self.initial_balance,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        
        # Load positions
        try:
            if os.path.exists(positions_file):
                with open(positions_file, 'r') as f:
                    self.positions = json.load(f)
            else:
                self.positions = []
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
            self.positions = []
        
        # Load orders
        try:
            if os.path.exists(orders_file):
                with open(orders_file, 'r') as f:
                    self.orders = json.load(f)
            else:
                self.orders = []
        except Exception as e:
            logger.error(f"Error loading orders: {e}")
            self.orders = []
    
    def _save_account_data(self):
        """Save account data to file"""
        account_file = os.path.join(self.data_dir, 'account.json')
        positions_file = os.path.join(self.data_dir, 'positions.json')
        orders_file = os.path.join(self.data_dir, 'orders.json')
        
        # Update account data
        self.account_data['updated_at'] = datetime.now().isoformat()
        
        # Save account data
        try:
            with open(account_file, 'w') as f:
                json.dump(self.account_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving account data: {e}")
        
        # Save positions
        try:
            with open(positions_file, 'w') as f:
                json.dump(self.positions, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
        
        # Save orders
        try:
            with open(orders_file, 'w') as f:
                json.dump(self.orders, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving orders: {e}")
    
    def _execute_order(self, order):
        """
        Execute an order (simulate fill)
        
        Args:
            order (dict): Order to execute
        """
        # Set fill price (in a real system, this would come from market data)
        if order['price'] is not None:
            fill_price = order['price']
        else:
            # Simulate a realistic fill price
            # In a real implementation, this would use real-time market data
            fill_price = 100.0  # Placeholder
        
        # Update order
        order['status'] = OrderStatus.FILLED.value
        order['updated_at'] = datetime.now().isoformat()
        order['filled_at'] = datetime.now().isoformat()
        order['filled_price'] = fill_price
        
        # Update positions and account balance
        if order['asset_type'] == 'stock':
            self._update_stock_position(order, fill_price)
        elif order['asset_type'] == 'option':
            self._update_option_position(order, fill_price)
    
    def _update_stock_position(self, order, fill_price):
        """
        Update stock position after order execution
        
        Args:
            order (dict): Executed order
            fill_price (float): Fill price
        """
        symbol = order['symbol']
        quantity = order['quantity']
        side = order['side']
        
        # Calculate transaction amount
        transaction_amount = quantity * fill_price
        
        # Find existing position
        existing_position = None
        for i, position in enumerate(self.positions):
            if position['symbol'] == symbol and position['asset_type'] == 'stock':
                existing_position = position
                position_index = i
                break
        
        # Update position
        if side == OrderSide.BUY.value:
            # Deduct from balance
            self.account_data['balance'] -= transaction_amount
            
            if existing_position:
                # Update existing position
                new_quantity = existing_position['quantity'] + quantity
                new_cost_basis = ((existing_position['quantity'] * existing_position['cost_basis']) + 
                                 (quantity * fill_price)) / new_quantity
                
                self.positions[position_index]['quantity'] = new_quantity
                self.positions[position_index]['cost_basis'] = new_cost_basis
                self.positions[position_index]['market_value'] = new_quantity * fill_price
                self.positions[position_index]['updated_at'] = datetime.now().isoformat()
            else:
                # Create new position
                new_position = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'cost_basis': fill_price,
                    'market_value': quantity * fill_price,
                    'asset_type': 'stock',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                self.positions.append(new_position)
        
        elif side == OrderSide.SELL.value:
            # Add to balance
            self.account_data['balance'] += transaction_amount
            
            if existing_position:
                # Update existing position
                new_quantity = existing_position['quantity'] - quantity
                
                if new_quantity > 0:
                    # Update position
                    self.positions[position_index]['quantity'] = new_quantity
                    self.positions[position_index]['market_value'] = new_quantity * fill_price
                    self.positions[position_index]['updated_at'] = datetime.now().isoformat()
                else:
                    # Remove position
                    self.positions.pop(position_index)
            else:
                logger.warning(f"Selling {quantity} shares of {symbol} without an existing position")
        
        # Update equity and buying power
        self._update_account_equity()
    
    def _update_option_position(self, order, fill_price):
        """
        Update option position after order execution
        
        Args:
            order (dict): Executed order
            fill_price (float): Fill price
        """
        option_symbol = order['option_symbol']
        quantity = order['quantity']
        side = order['side']
        
        # Calculate transaction amount (options are priced per share, but sold in contracts of 100 shares)
        transaction_amount = quantity * fill_price * 100
        
        # Find existing position
        existing_position = None
        for i, position in enumerate(self.positions):
            if position.get('option_symbol') == option_symbol and position['asset_type'] == 'option':
                existing_position = position
                position_index = i
                break
        
        # Update position based on order side
        if side in [OrderSide.BUY_TO_OPEN.value, OrderSide.BUY_TO_CLOSE.value]:
            # Deduct from balance
            self.account_data['balance'] -= transaction_amount
            
            if side == OrderSide.BUY_TO_OPEN.value:
                if existing_position:
                    # Update existing long position
                    new_quantity = existing_position['quantity'] + quantity
                    new_cost_basis = ((existing_position['quantity'] * existing_position['cost_basis']) + 
                                     (quantity * fill_price)) / new_quantity
                    
                    self.positions[position_index]['quantity'] = new_quantity
                    self.positions[position_index]['cost_basis'] = new_cost_basis
                    self.positions[position_index]['market_value'] = new_quantity * fill_price * 100
                    self.positions[position_index]['updated_at'] = datetime.now().isoformat()
                else:
                    # Create new long position
                    new_position = {
                        'symbol': order['symbol'],
                        'option_symbol': option_symbol,
                        'expiry': order['expiry'],
                        'strike': order['strike'],
                        'option_type': order['option_type'],
                        'quantity': quantity,
                        'cost_basis': fill_price,
                        'market_value': quantity * fill_price * 100,
                        'asset_type': 'option',
                        'position_type': 'long',
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    self.positions.append(new_position)
            
            elif side == OrderSide.BUY_TO_CLOSE.value:
                if existing_position and existing_position.get('position_type') == 'short':
                    # Close short position
                    new_quantity = existing_position['quantity'] - quantity
                    
                    if new_quantity > 0:
                        # Update position
                        self.positions[position_index]['quantity'] = new_quantity
                        self.positions[position_index]['market_value'] = new_quantity * fill_price * 100
                        self.positions[position_index]['updated_at'] = datetime.now().isoformat()
                    else:
                        # Remove position
                        self.positions.pop(position_index)
                else:
                    logger.warning(f"Buying to close {quantity} contracts of {option_symbol} without a short position")
        
        elif side in [OrderSide.SELL_TO_OPEN.value, OrderSide.SELL_TO_CLOSE.value]:
            # Add to balance
            self.account_data['balance'] += transaction_amount
            
            if side == OrderSide.SELL_TO_OPEN.value:
                if existing_position:
                    # Update existing short position
                    new_quantity = existing_position['quantity'] + quantity
                    new_cost_basis = ((existing_position['quantity'] * existing_position['cost_basis']) + 
                                     (quantity * fill_price)) / new_quantity
                    
                    self.positions[position_index]['quantity'] = new_quantity
                    self.positions[position_index]['cost_basis'] = new_cost_basis
                    self.positions[position_index]['market_value'] = new_quantity * fill_price * 100
                    self.positions[position_index]['updated_at'] = datetime.now().isoformat()
                else:
                    # Create new short position
                    new_position = {
                        'symbol': order['symbol'],
                        'option_symbol': option_symbol,
                        'expiry': order['expiry'],
                        'strike': order['strike'],
                        'option_type': order['option_type'],
                        'quantity': quantity,
                        'cost_basis': fill_price,
                        'market_value': quantity * fill_price * 100,
                        'asset_type': 'option',
                        'position_type': 'short',
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    self.positions.append(new_position)
            
            elif side == OrderSide.SELL_TO_CLOSE.value:
                if existing_position and existing_position.get('position_type') == 'long':
                    # Close long position
                    new_quantity = existing_position['quantity'] - quantity
                    
                    if new_quantity > 0:
                        # Update position
                        self.positions[position_index]['quantity'] = new_quantity
                        self.positions[position_index]['market_value'] = new_quantity * fill_price * 100
                        self.positions[position_index]['updated_at'] = datetime.now().isoformat()
                    else:
                        # Remove position
                        self.positions.pop(position_index)
                else:
                    logger.warning(f"Selling to close {quantity} contracts of {option_symbol} without a long position")
        
        # Update equity and buying power
        self._update_account_equity()
    
    def _update_account_equity(self):
        """Update account equity based on positions"""
        # Calculate total position value
        position_value = sum(position['market_value'] for position in self.positions)
        
        # Update equity
        self.account_data['equity'] = self.account_data['balance'] + position_value
        
        # Update buying power (simplified)
        self.account_data['buying_power'] = self.account_data['balance']
