#!/usr/bin/env python3
"""
Strategy Configuration Module for Trading Bot
-------------------------------------------
Handles reading and writing strategy configuration files
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger('trading_bot.strategy_config')

# Default strategy configuration
DEFAULT_STRATEGY_CONFIG = {
    "version": "1.0.0",
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "general": {
        "risk_per_trade": 0.02,  # 2% of account per trade
        "max_positions": 5,      # Maximum number of concurrent positions
        "position_sizing": "risk_based"  # Options: fixed, risk_based, kelly
    },
    "technical_indicators": {
        "use_sma": True,
        "use_ema": True,
        "use_macd": True,
        "use_rsi": True,
        "use_bollinger": True,
        "sma_periods": [20, 50, 200],
        "ema_periods": [12, 26],
        "macd_params": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9
        },
        "rsi_period": 14,
        "bollinger_period": 20,
        "bollinger_std": 2.0
    },
    "options_strategies": {
        "default_strategy": "auto",  # Options: auto, long_call, long_put, bull_put_spread, bear_call_spread, iron_condor
        "stop_loss_pct": 0.5,        # Exit if option loses 50% of its value
        "take_profit_pct": 1.0,      # Exit if option gains 100% of its value
        "max_days_to_hold": 14,      # Maximum number of days to hold an options position
        "strategy_selection": {
            "bullish": {
                "low_iv": "long_call",
                "high_iv": "bull_put_spread",
                "iv_threshold": 0.5
            },
            "bearish": {
                "low_iv": "long_put",
                "high_iv": "bear_call_spread",
                "iv_threshold": 0.5
            },
            "neutral": {
                "default": "iron_condor"
            }
        },
        "expiration_selection": "nearest",  # Options: nearest, monthly, weekly
        "strike_selection": {
            "call_itm_pct": 0.03,  # 3% in-the-money
            "call_otm_pct": 0.05,  # 5% out-of-the-money
            "put_itm_pct": 0.03,   # 3% in-the-money
            "put_otm_pct": 0.05    # 5% out-of-the-money
        }
    },
    "signals": {
        "trend_weight": 0.4,
        "momentum_weight": 0.3,
        "volatility_weight": 0.3,
        "signal_threshold": 0.2,  # Signal strength threshold
        "confirmation_required": True  # Require multiple indicator confirmation
    },
    "backtest": {
        "initial_capital": 100000,
        "commission_per_contract": 0.65,
        "slippage_pct": 0.01
    }
}


def load_strategy_config(config_path=None):
    """
    Load strategy configuration from a JSON file
    
    Args:
        config_path (str): Path to the configuration file
        
    Returns:
        dict: Strategy configuration
    """
    if not config_path:
        logger.info("No configuration file specified, using default configuration")
        return DEFAULT_STRATEGY_CONFIG.copy()
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded strategy configuration from {config_path}")
            
            # Merge with defaults to ensure all required fields exist
            merged_config = DEFAULT_STRATEGY_CONFIG.copy()
            _deep_update(merged_config, config)
            
            return merged_config
        else:
            logger.warning(f"Configuration file {config_path} not found, using default configuration")
            return DEFAULT_STRATEGY_CONFIG.copy()
    except Exception as e:
        logger.error(f"Error loading configuration file: {e}")
        logger.info("Using default configuration")
        return DEFAULT_STRATEGY_CONFIG.copy()


def save_strategy_config(config, config_path):
    """
    Save strategy configuration to a JSON file
    
    Args:
        config (dict): Strategy configuration
        config_path (str): Path to save the configuration file
    """
    try:
        # Update the last_updated timestamp
        config["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Saved strategy configuration to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration file: {e}")
        return False


def extract_current_strategy(config):
    """
    Extract the current strategy settings from the configuration
    
    Args:
        config (dict): Strategy configuration
        
    Returns:
        dict: Current strategy settings
    """
    current_strategy = {
        "version": config.get("version", "1.0.0"),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "options_strategies": config.get("options_strategies", {}),
        "technical_indicators": config.get("technical_indicators", {})
    }
    
    return current_strategy


def _deep_update(target, source):
    """
    Deep update a nested dictionary
    
    Args:
        target (dict): Target dictionary to update
        source (dict): Source dictionary with updates
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
