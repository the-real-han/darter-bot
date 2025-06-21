# Greek-Based Options Strategy Optimization

This module enhances the trading bot with sophisticated options strategy selection based on option Greeks provided by Polygon.io.

## Overview

The Greek optimizer uses option Greeks (delta, gamma, theta, vega) to select the most appropriate options contracts and strategies based on market conditions and trading objectives.

## Key Features

1. **Greek-Based Contract Selection**
   - Selects options with optimal delta for directional exposure
   - Prioritizes high gamma for acceleration trades
   - Minimizes theta decay for longer-term positions
   - Maximizes vega for volatility plays

2. **Strategy Optimization**
   - **Directional Trades**: Optimizes long calls/puts based on Greeks
   - **Volatility Trades**: Creates straddles/strangles or iron condors based on volatility outlook
   - **Theta Decay Trades**: Designs credit spreads to maximize theta decay
   - **Gamma Scalping**: Identifies high gamma opportunities for short-term trading

3. **Risk Management**
   - Calculates optimal position sizing based on risk parameters
   - Filters for liquidity using open interest and volume
   - Considers bid-ask spreads for execution quality

## Configuration

The Greek optimizer can be configured in your strategy JSON file:

```json
{
  "use_greek_optimization": true,
  "volatility_bias": "neutral",
  "greek_optimization": {
    "delta_threshold": 0.5,
    "gamma_threshold": 0.1,
    "theta_threshold": -0.1,
    "vega_threshold": 0.2,
    "min_open_interest": 50,
    "min_volume": 5,
    "max_bid_ask_spread": 0.1
  }
}
```

### Configuration Parameters

- **use_greek_optimization**: Enable/disable Greek-based optimization
- **volatility_bias**: Set to "increasing", "decreasing", or "neutral"
- **delta_threshold**: Target delta for directional trades (0.0-1.0)
- **gamma_threshold**: Minimum gamma for acceleration trades
- **theta_threshold**: Maximum theta decay acceptable
- **vega_threshold**: Minimum vega for volatility trades
- **min_open_interest**: Minimum open interest for liquidity
- **min_volume**: Minimum trading volume for liquidity
- **max_bid_ask_spread**: Maximum acceptable bid-ask spread as percentage

## Strategy Types

### Directional Strategies

For bullish or bearish market outlooks, the optimizer selects options with:
- Delta close to the target threshold
- Higher gamma for acceleration potential
- Less negative theta to minimize time decay
- Appropriate liquidity for easy entry/exit

### Volatility Strategies

For volatility-based trading:
- **Increasing Volatility**: Long straddles/strangles with high positive vega
- **Decreasing Volatility**: Iron condors or short straddles with negative vega

### Theta Decay Strategies

For income generation through time decay:
- Credit spreads with maximum theta decay
- Balanced delta exposure to minimize directional risk
- Appropriate width between short and long strikes

### Gamma Scalping Strategies

For short-term trading around a price level:
- At-the-money options with high gamma
- Moderate delta for directional exposure
- Balance between gamma and theta

## Integration with Polygon.io

The Greek optimizer leverages the option Greeks provided by Polygon.io's options snapshot API:
- Delta: Sensitivity to underlying price changes
- Gamma: Rate of change of delta
- Theta: Time decay per day
- Vega: Sensitivity to volatility changes
- Rho: Sensitivity to interest rate changes

## Usage

The Greek optimizer is automatically used when:
1. `use_greek_optimization` is set to `true` in your configuration
2. The options data from Polygon.io includes Greek values

You can also specify a volatility bias to influence strategy selection:
```bash
python options_main.py --config custom_strategy.json
```

Where `custom_strategy.json` includes your Greek optimization settings.

## Benefits

1. **More Precise Strategy Selection**: Uses quantitative metrics rather than rules of thumb
2. **Optimized Risk/Reward**: Balances potential gains against risks
3. **Liquidity Consideration**: Avoids illiquid options that may be difficult to trade
4. **Adaptability**: Adjusts to different market conditions automatically
