#!/usr/bin/env python3
"""
Investopedia Trading Platform Module
---------------------------------
Implements the Investopedia Stock Simulator trading platform
"""

import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from .base_platform import BaseTradingPlatform, OrderType, OrderSide, OrderStatus

logger = logging.getLogger('trading_bot.trading_platforms.investopedia')

class InvestopediaPlatform(BaseTradingPlatform):
    """Investopedia Stock Simulator trading platform implementation"""
    
    BASE_URL = "https://www.investopedia.com"
    LOGIN_URL = f"{BASE_URL}/accounts/signin"
    PORTFOLIO_URL = f"{BASE_URL}/simulator/portfolio"
    TRADE_URL = f"{BASE_URL}/simulator/trade"
    ORDERS_URL = f"{BASE_URL}/simulator/open-orders"
    
    def __init__(self, auth_token=None, username=None, password=None, **kwargs):
        """
        Initialize the trading platform
        
        Args:
            auth_token (str): Authentication bearer token for Investopedia
            username (str): Username for the trading platform (legacy)
            password (str): Password for the trading platform (legacy)
            **kwargs: Additional platform-specific parameters
        """
        self.auth_token = auth_token
        self.username = username
        self.password = password
        self.client = None
        self.authenticated = False
        self.initialize_client(**kwargs)
    
    def initialize_client(self, **kwargs):
        """Initialize the Investopedia client"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add authorization header if token is provided
        if self.auth_token:
            self.headers['Authorization'] = f"Bearer {self.auth_token}"
        
        self.session.headers.update(self.headers)
        self.client = self.session
        logger.info("Investopedia client initialized")
    
    def authenticate(self):
        """
        Authenticate with Investopedia
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        # If auth token is provided, use token-based authentication
        if self.auth_token:
            try:
                # Test authentication by accessing portfolio page
                response = self.session.get(self.PORTFOLIO_URL)
                
                # Check if authentication was successful
                if response.status_code == 200 and 'Sign In' not in response.text:
                    self.authenticated = True
                    logger.info("Successfully authenticated with Investopedia using bearer token")
                    return True
                else:
                    logger.error("Failed to authenticate with Investopedia using bearer token")
                    return False
            except Exception as e:
                logger.error(f"Error authenticating with Investopedia using bearer token: {e}")
                return False
        
        # Fall back to username/password authentication if provided
        elif self.username and self.password:
            try:
                # First, get the login page to extract CSRF token
                login_page = self.session.get(self.LOGIN_URL)
                soup = BeautifulSoup(login_page.text, 'html.parser')
                
                # Find the CSRF token
                csrf_token = None
                csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
                if csrf_input:
                    csrf_token = csrf_input.get('value')
                
                if not csrf_token:
                    logger.error("Could not find CSRF token on login page")
                    return False
                
                # Prepare login data
                login_data = {
                    'csrfmiddlewaretoken': csrf_token,
                    'username': self.username,
                    'password': self.password,
                    'next': '/simulator/home'
                }
                
                # Set referer header
                self.session.headers.update({'Referer': self.LOGIN_URL})
                
                # Submit login form
                response = self.session.post(self.LOGIN_URL, data=login_data)
                
                # Check if login was successful
                if response.url.endswith('/simulator/home') or 'simulator/portfolio' in response.url:
                    self.authenticated = True
                    logger.info("Successfully authenticated with Investopedia using username/password")
                    return True
                else:
                    logger.error("Failed to authenticate with Investopedia using username/password")
                    return False
                    
            except Exception as e:
                logger.error(f"Error authenticating with Investopedia using username/password: {e}")
                return False
        else:
            logger.error("Either auth_token or username/password are required for Investopedia authentication")
            return False
    
    def get_account_info(self):
        """
        Get account information from Investopedia
        
        Returns:
            dict: Account information
        """
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Authentication required to get account information")
                return {}
        
        try:
            # Get portfolio page
            response = self.session.get(self.PORTFOLIO_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract account value
            account_value = None
            account_value_elem = soup.select_one('.simulator-user-account-value')
            if account_value_elem:
                account_value_text = account_value_elem.text.strip()
                account_value = self._parse_currency(account_value_text)
            
            # Extract buying power
            buying_power = None
            buying_power_elem = soup.select_one('.simulator-user-buying-power')
            if buying_power_elem:
                buying_power_text = buying_power_elem.text.strip()
                buying_power = self._parse_currency(buying_power_text)
            
            # Extract cash
            cash = None
            cash_elem = soup.select_one('.simulator-user-cash')
            if cash_elem:
                cash_text = cash_elem.text.strip()
                cash = self._parse_currency(cash_text)
            
            # Extract annual return
            annual_return = None
            annual_return_elem = soup.select_one('.simulator-user-annual-return-value')
            if annual_return_elem:
                annual_return_text = annual_return_elem.text.strip()
                annual_return = self._parse_percentage(annual_return_text)
            
            account_info = {
                'account_value': account_value,
                'buying_power': buying_power,
                'cash': cash,
                'annual_return': annual_return,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("Successfully retrieved account information")
            return account_info
            
        except Exception as e:
            logger.error(f"Error getting account information: {e}")
            return {}
    
    def get_positions(self):
        """
        Get current positions from Investopedia
        
        Returns:
            list: List of positions
        """
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Authentication required to get positions")
                return []
        
        try:
            # Get portfolio page
            response = self.session.get(self.PORTFOLIO_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the positions table
            positions_table = soup.select_one('table.table-bordered.table-striped.simulator-holdings-table')
            if not positions_table:
                logger.warning("No positions table found")
                return []
            
            positions = []
            rows = positions_table.select('tbody tr')
            
            for row in rows:
                cells = row.select('td')
                if len(cells) < 7:
                    continue
                
                # Extract position data
                symbol = cells[0].text.strip()
                quantity = self._parse_integer(cells[1].text.strip())
                purchase_price = self._parse_currency(cells[2].text.strip())
                current_price = self._parse_currency(cells[3].text.strip())
                market_value = self._parse_currency(cells[4].text.strip())
                day_change = self._parse_currency(cells[5].text.strip())
                total_change = self._parse_currency(cells[6].text.strip())
                
                position = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'purchase_price': purchase_price,
                    'current_price': current_price,
                    'market_value': market_value,
                    'day_change': day_change,
                    'total_change': total_change
                }
                
                positions.append(position)
            
            logger.info(f"Successfully retrieved {len(positions)} positions")
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_orders(self, status=None):
        """
        Get orders from Investopedia
        
        Args:
            status (OrderStatus): Filter orders by status
            
        Returns:
            list: List of orders
        """
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Authentication required to get orders")
                return []
        
        try:
            # Get open orders page
            response = self.session.get(self.ORDERS_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the orders table
            orders_table = soup.select_one('table.table-bordered.table-striped')
            if not orders_table:
                logger.warning("No orders table found")
                return []
            
            orders = []
            rows = orders_table.select('tbody tr')
            
            for row in rows:
                cells = row.select('td')
                if len(cells) < 6:
                    continue
                
                # Extract order data
                order_id = cells[0].text.strip()
                symbol = cells[1].text.strip()
                order_type_text = cells[2].text.strip()
                quantity = self._parse_integer(cells[3].text.strip())
                price = self._parse_currency(cells[4].text.strip())
                date = cells[5].text.strip()
                
                # Parse order type and side
                side = OrderSide.BUY
                order_type = OrderType.MARKET
                
                if "sell" in order_type_text.lower():
                    side = OrderSide.SELL
                
                if "limit" in order_type_text.lower():
                    order_type = OrderType.LIMIT
                elif "stop" in order_type_text.lower():
                    order_type = OrderType.STOP
                
                order = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'order_type': order_type,
                    'quantity': quantity,
                    'price': price,
                    'date': date,
                    'status': OrderStatus.PENDING
                }
                
                # Filter by status if provided
                if status is None or order['status'] == status:
                    orders.append(order)
            
            logger.info(f"Successfully retrieved {len(orders)} orders")
            return orders
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def place_stock_order(self, symbol, quantity, side, order_type=OrderType.MARKET, price=None, stop_price=None):
        """
        Place a stock order on Investopedia
        
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
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Authentication required to place order")
                return {}
        
        try:
            # Get trade page to extract form tokens
            response = self.session.get(self.TRADE_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the CSRF token
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            if not csrf_token:
                logger.error("Could not find CSRF token on trade page")
                return {}
            
            # Prepare order data
            order_data = {
                'csrfmiddlewaretoken': csrf_token,
                'symbol': symbol,
                'quantity': str(quantity),
                'tradeType': 'stock'
            }
            
            # Set order side
            if side == OrderSide.BUY:
                order_data['transactionType'] = 'buy'
            elif side == OrderSide.SELL:
                order_data['transactionType'] = 'sell'
            else:
                logger.error(f"Unsupported order side: {side}")
                return {}
            
            # Set order type and price
            if order_type == OrderType.MARKET:
                order_data['priceType'] = 'market'
            elif order_type == OrderType.LIMIT:
                order_data['priceType'] = 'limit'
                order_data['limitPrice'] = str(price)
            elif order_type == OrderType.STOP:
                order_data['priceType'] = 'stop'
                order_data['stopPrice'] = str(stop_price)
            elif order_type == OrderType.STOP_LIMIT:
                order_data['priceType'] = 'stopLimit'
                order_data['limitPrice'] = str(price)
                order_data['stopPrice'] = str(stop_price)
            else:
                logger.error(f"Unsupported order type: {order_type}")
                return {}
            
            # Set term (day order)
            order_data['term'] = 'day'
            
            # Set referer header
            self.session.headers.update({'Referer': self.TRADE_URL})
            
            # Submit order form
            response = self.session.post(self.TRADE_URL, data=order_data)
            
            # Check if order was successful
            if "order has been successfully submitted" in response.text:
                logger.info(f"Successfully placed {side.value} order for {quantity} shares of {symbol}")
                
                # Try to extract order ID
                order_id = None
                match = re.search(r'Order ID: (\d+)', response.text)
                if match:
                    order_id = match.group(1)
                
                return {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side,
                    'order_type': order_type,
                    'price': price,
                    'stop_price': stop_price,
                    'status': OrderStatus.PENDING,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.error(f"Failed to place order: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error placing stock order: {e}")
            return {}
    
    def place_option_order(self, symbol, expiry, strike, option_type, quantity, side, order_type=OrderType.MARKET, price=None):
        """
        Place an option order on Investopedia
        
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
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Authentication required to place option order")
                return {}
        
        try:
            # Get trade page to extract form tokens
            response = self.session.get(self.TRADE_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the CSRF token
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            if not csrf_token:
                logger.error("Could not find CSRF token on trade page")
                return {}
            
            # Format expiry date for Investopedia (MM/DD/YYYY)
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d')
            formatted_expiry = expiry_date.strftime('%m/%d/%Y')
            
            # Format strike price
            formatted_strike = f"{strike:.2f}"
            
            # Prepare option symbol (e.g., AAPL220121C00150000)
            option_symbol = f"{symbol}{formatted_expiry}{option_type[0].upper()}{formatted_strike}"
            
            # Prepare order data
            order_data = {
                'csrfmiddlewaretoken': csrf_token,
                'symbol': option_symbol,
                'quantity': str(quantity),
                'tradeType': 'option'
            }
            
            # Set order side
            if side == OrderSide.BUY_TO_OPEN:
                order_data['transactionType'] = 'buy'
                order_data['openClose'] = 'open'
            elif side == OrderSide.SELL_TO_OPEN:
                order_data['transactionType'] = 'sell'
                order_data['openClose'] = 'open'
            elif side == OrderSide.BUY_TO_CLOSE:
                order_data['transactionType'] = 'buy'
                order_data['openClose'] = 'close'
            elif side == OrderSide.SELL_TO_CLOSE:
                order_data['transactionType'] = 'sell'
                order_data['openClose'] = 'close'
            else:
                logger.error(f"Unsupported order side for options: {side}")
                return {}
            
            # Set order type and price
            if order_type == OrderType.MARKET:
                order_data['priceType'] = 'market'
            elif order_type == OrderType.LIMIT:
                order_data['priceType'] = 'limit'
                order_data['limitPrice'] = str(price)
            else:
                logger.error(f"Unsupported order type for options: {order_type}")
                return {}
            
            # Set term (day order)
            order_data['term'] = 'day'
            
            # Set referer header
            self.session.headers.update({'Referer': self.TRADE_URL})
            
            # Submit order form
            response = self.session.post(self.TRADE_URL, data=order_data)
            
            # Check if order was successful
            if "order has been successfully submitted" in response.text:
                logger.info(f"Successfully placed {side.value} order for {quantity} contracts of {option_symbol}")
                
                # Try to extract order ID
                order_id = None
                match = re.search(r'Order ID: (\d+)', response.text)
                if match:
                    order_id = match.group(1)
                
                return {
                    'order_id': order_id,
                    'symbol': symbol,
                    'option_symbol': option_symbol,
                    'expiry': expiry,
                    'strike': strike,
                    'option_type': option_type,
                    'quantity': quantity,
                    'side': side,
                    'order_type': order_type,
                    'price': price,
                    'status': OrderStatus.PENDING,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.error(f"Failed to place option order: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error placing option order: {e}")
            return {}
    
    def cancel_order(self, order_id):
        """
        Cancel an order on Investopedia
        
        Args:
            order_id (str): Order ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Authentication required to cancel order")
                return False
        
        try:
            # Construct cancel URL
            cancel_url = f"{self.ORDERS_URL}/cancel/{order_id}"
            
            # Send cancel request
            response = self.session.get(cancel_url)
            
            # Check if cancellation was successful
            if response.status_code == 200 and "order has been cancelled" in response.text:
                logger.info(f"Successfully cancelled order {order_id}")
                return True
            else:
                logger.error(f"Failed to cancel order {order_id}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id):
        """
        Get order status from Investopedia
        
        Args:
            order_id (str): Order ID
            
        Returns:
            OrderStatus: Order status
        """
        if not self.authenticated:
            if not self.authenticate():
                logger.error("Authentication required to get order status")
                return OrderStatus.REJECTED
        
        try:
            # Get open orders
            orders = self.get_orders()
            
            # Find the order with matching ID
            for order in orders:
                if order['order_id'] == order_id:
                    return order['status']
            
            # If order not found in open orders, check order history
            # (This would require implementing a method to get order history)
            
            # If not found in either, assume it's been filled
            logger.info(f"Order {order_id} not found in open orders, assuming filled")
            return OrderStatus.FILLED
            
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {e}")
            return OrderStatus.REJECTED
    
    def _parse_currency(self, text):
        """Parse currency value from text"""
        if not text:
            return None
        
        # Remove currency symbols and commas
        clean_text = text.replace('$', '').replace(',', '').strip()
        
        try:
            # Handle negative values
            if '(' in clean_text and ')' in clean_text:
                clean_text = clean_text.replace('(', '-').replace(')', '')
            
            return float(clean_text)
        except ValueError:
            return None
    
    def _parse_percentage(self, text):
        """Parse percentage value from text"""
        if not text:
            return None
        
        # Remove percentage symbol and commas
        clean_text = text.replace('%', '').replace(',', '').strip()
        
        try:
            # Handle negative values
            if '(' in clean_text and ')' in clean_text:
                clean_text = clean_text.replace('(', '-').replace(')', '')
            
            return float(clean_text) / 100.0
        except ValueError:
            return None
    
    def _parse_integer(self, text):
        """Parse integer value from text"""
        if not text:
            return None
        
        # Remove commas
        clean_text = text.replace(',', '').strip()
        
        try:
            return int(clean_text)
        except ValueError:
            return None
