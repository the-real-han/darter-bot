#!/usr/bin/env python3
"""
Data Provider Factory Module
-------------------------
Factory for creating data provider instances
"""

import logging
from .finnhub_provider import FinnhubDataProvider
from .yahoo_provider import YahooDataProvider
from .polygon_provider import PolygonDataProvider

logger = logging.getLogger('trading_bot.data_providers.factory')

class DataProviderFactory:
    """Factory for creating data provider instances"""
    
    @staticmethod
    def get_provider(provider_name, api_key=None, **kwargs):
        """
        Get a data provider instance
        
        Args:
            provider_name (str): Name of the provider ('finnhub', 'yahoo', 'polygon', etc.)
            api_key (str): API key for the provider
            **kwargs: Additional provider-specific parameters
            
        Returns:
            BaseDataProvider: Data provider instance
        """
        provider_name = provider_name.lower()
        
        if provider_name == 'finnhub':
            logger.info("Creating Finnhub data provider")
            return FinnhubDataProvider(api_key=api_key, **kwargs)
        elif provider_name == 'yahoo':
            logger.info("Creating Yahoo Finance data provider")
            return YahooDataProvider(api_key=None, **kwargs)
        elif provider_name == 'polygon':
            logger.info("Creating Polygon.io data provider")
            return PolygonDataProvider(api_key=api_key, **kwargs)
        else:
            logger.warning(f"Unknown provider '{provider_name}', falling back to Yahoo Finance")
            return YahooDataProvider(api_key=None, **kwargs)
