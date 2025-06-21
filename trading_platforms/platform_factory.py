#!/usr/bin/env python3
"""
Trading Platform Factory Module
----------------------------
Factory for creating trading platform instances
"""

import logging
from .investopedia_platform import InvestopediaPlatform
from .paper_platform import PaperTradingPlatform

logger = logging.getLogger('trading_bot.trading_platforms.factory')

class TradingPlatformFactory:
    """Factory for creating trading platform instances"""
    
    @staticmethod
    def get_platform(platform_name, **kwargs):
        """
        Get a trading platform instance
        
        Args:
            platform_name (str): Name of the platform ('investopedia', 'paper', etc.)
            **kwargs: Platform-specific parameters
            
        Returns:
            BaseTradingPlatform: Trading platform instance
        """
        platform_name = platform_name.lower()
        
        if platform_name == 'investopedia':
            logger.info("Creating Investopedia trading platform")
            return InvestopediaPlatform(**kwargs)
        elif platform_name == 'paper':
            logger.info("Creating Paper trading platform")
            return PaperTradingPlatform(**kwargs)
        else:
            logger.warning(f"Unknown platform '{platform_name}', falling back to Paper trading")
            return PaperTradingPlatform(**kwargs)
