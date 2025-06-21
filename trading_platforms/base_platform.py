#!/usr/bin/env python3
"""
Base Trading Platform Module
-------------------------
Defines the interface for trading platforms
"""

from abc import ABC, abstractmethod
from enum import Enum
import logging

logger = logging.getLogger('trading_bot.trading_platforms')

class OrderType(Enum):
    """Order types for trading platforms"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    """Order sides for trading platforms"""
    BUY = "buy"
    SELL = "sell"
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"

class OrderStatus(Enum):
    """Order statuses for trading platforms"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class BaseTradingPlatform(ABC):
    """Base class for trading platforms"""
    
    def __init__(self, username=None, password=None, **kwargs):
        """
        Initialize the trading platform
        
        Args:
            username (str): Username for the trading platform
            password (str): Password for the trading platform
            **kwargs: Additional platform-specific parameters
        """
        self.username = username
        self.password = password
        self.client = None
        self.authenticated = False
        self.initialize_client(**kwargs)
    
    @abstractmethod
    def initialize_client(self, **kwargs):
        """Initialize the trading platform client"""
        pass
    
    @abstractmethod
    def authenticate(self):
        """Authenticate with the trading platform"""
        pass
    
    @abstractmethod
    def get_account_info(self):
        """
        Get account information
        
        Returns:
            dict: Account information
        """
        pass
    
    @abstractmethod
    def get_positions(self):
        """
        Get current positions
        
        Returns:
            list: List of positions
        """
        pass
    
    @abstractmethod
    def get_orders(self, status=None):
        """
        Get orders
        
        Args:
            status (OrderStatus): Filter orders by status
            
        Returns:
            list: List of orders
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def cancel_order(self, order_id):
        """
        Cancel an order
        
        Args:
            order_id (str): Order ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id):
        """
        Get order status
        
        Args:
            order_id (str): Order ID
            
        Returns:
            OrderStatus: Order status
        """
        pass
