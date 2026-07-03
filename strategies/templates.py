"""
Pre-built strategy templates for the Strategy Lab Template Gallery.
Each template is a complete strategy definition (columns + signal_rule)
that users can clone and customize.
"""

STRATEGY_TEMPLATES = [
    {
        "id": "golden_cross",
        "name": "Golden Cross",
        "description": "Classic trend-following strategy using SMA 50/200 crossover. Buys when the 50-day SMA crosses above the 200-day SMA (bullish), sells when it crosses below (bearish). Best suited for long-term trend trading on major indices and large-cap stocks.",
        "category": "Trend Following",
        "columns": [
            {"name": "sma_50", "formula": "close.rolling(50).mean()"},
            {"name": "sma_200", "formula": "close.rolling(200).mean()"},
        ],
        "signal_rule": "sma_50 > sma_200 : 1, sma_50 < sma_200 : -1, True : 0",
        "tags": ["SMA", "crossover", "long-term"],
    },
    {
        "id": "rsi_mean_reversion",
        "name": "RSI Mean Reversion",
        "description": "Mean reversion strategy using RSI(14). Buys when RSI drops below 30 (oversold), sells when RSI rises above 70 (overbought). Works well in range-bound markets and on stocks that tend to revert to their mean.",
        "category": "Mean Reversion",
        "columns": [
            {"name": "rsi_delta", "formula": "close.diff()"},
            {"name": "rsi_gain", "formula": "rsi_delta.clip(lower=0)"},
            {"name": "rsi_loss", "formula": "-rsi_delta.clip(upper=0)"},
            {"name": "rsi_avg_gain", "formula": "rsi_gain.rolling(14).mean()"},
            {"name": "rsi_avg_loss", "formula": "rsi_loss.rolling(14).mean()"},
            {"name": "rsi_rs", "formula": "rsi_avg_gain / rsi_avg_loss"},
            {"name": "rsi", "formula": "100 - (100 / (1 + rsi_rs))"},
        ],
        "signal_rule": "rsi < 30 : 1, rsi > 70 : -1, True : 0",
        "tags": ["RSI", "oversold", "overbought"],
    },
    {
        "id": "macd_momentum",
        "name": "MACD Momentum",
        "description": "Momentum strategy using MACD(12,26,9). Generates buy signals when the MACD histogram turns positive (bullish momentum) and sell signals when it turns negative. Effective for capturing medium-term momentum shifts.",
        "category": "Momentum",
        "columns": [
            {"name": "macd_fast", "formula": "close.ewm(span=12, adjust=False).mean()"},
            {"name": "macd_slow", "formula": "close.ewm(span=26, adjust=False).mean()"},
            {"name": "macd_line", "formula": "macd_fast - macd_slow"},
            {"name": "macd_signal", "formula": "macd_line.ewm(span=9, adjust=False).mean()"},
            {"name": "macd_hist", "formula": "macd_line - macd_signal"},
        ],
        "signal_rule": "macd_hist > 0 : 1, macd_hist < 0 : -1, True : 0",
        "tags": ["MACD", "EMA", "histogram"],
    },
    {
        "id": "bollinger_squeeze",
        "name": "Bollinger Squeeze",
        "description": "Volatility-based strategy using Bollinger Bands(20,2). Buys when price touches the lower band (potential bounce) and sells when price reaches the upper band (potential reversal). Ideal for range-bound markets with predictable volatility cycles.",
        "category": "Volatility",
        "columns": [
            {"name": "bb_mid", "formula": "close.rolling(20).mean()"},
            {"name": "bb_std", "formula": "close.rolling(20).std()"},
            {"name": "bb_upper", "formula": "bb_mid + 2 * bb_std"},
            {"name": "bb_lower", "formula": "bb_mid - 2 * bb_std"},
        ],
        "signal_rule": "close < bb_lower : 1, close > bb_upper : -1, True : 0",
        "tags": ["Bollinger Bands", "volatility", "mean reversion"],
    },
    {
        "id": "ema_crossover",
        "name": "EMA Crossover",
        "description": "Short-term trend strategy using EMA 9/21 crossover. Faster than SMA-based crossovers, making it more responsive to recent price changes. Buys when fast EMA crosses above slow EMA, sells when it crosses below. Good for swing trading.",
        "category": "Trend Following",
        "columns": [
            {"name": "ema_9", "formula": "close.ewm(span=9, adjust=False).mean()"},
            {"name": "ema_21", "formula": "close.ewm(span=21, adjust=False).mean()"},
        ],
        "signal_rule": "ema_9 > ema_21 : 1, ema_9 < ema_21 : -1, True : 0",
        "tags": ["EMA", "crossover", "swing trading"],
    },
    {
        "id": "dual_rsi_filter",
        "name": "Dual RSI Filter",
        "description": "Enhanced mean reversion using two RSI periods (7 and 14). Only generates buy signals when both short-term RSI(7) and medium-term RSI(14) agree on oversold conditions, reducing false signals compared to single-RSI strategies.",
        "category": "Mean Reversion",
        "columns": [
            {"name": "rsi_delta", "formula": "close.diff()"},
            {"name": "rsi_gain", "formula": "rsi_delta.clip(lower=0)"},
            {"name": "rsi_loss", "formula": "-rsi_delta.clip(upper=0)"},
            {"name": "rsi7_avg_gain", "formula": "rsi_gain.rolling(7).mean()"},
            {"name": "rsi7_avg_loss", "formula": "rsi_loss.rolling(7).mean()"},
            {"name": "rsi7_rs", "formula": "rsi7_avg_gain / rsi7_avg_loss"},
            {"name": "rsi_7", "formula": "100 - (100 / (1 + rsi7_rs))"},
            {"name": "rsi14_avg_gain", "formula": "rsi_gain.rolling(14).mean()"},
            {"name": "rsi14_avg_loss", "formula": "rsi_loss.rolling(14).mean()"},
            {"name": "rsi14_rs", "formula": "rsi14_avg_gain / rsi14_avg_loss"},
            {"name": "rsi_14", "formula": "100 - (100 / (1 + rsi14_rs))"},
        ],
        "signal_rule": "(rsi_7 < 30) & (rsi_14 < 40) : 1, (rsi_7 > 70) & (rsi_14 > 60) : -1, True : 0",
        "tags": ["RSI", "dual filter", "confirmation"],
    },
    {
        "id": "atr_breakout",
        "name": "ATR Breakout",
        "description": "Volatility breakout strategy using ATR(14). Buys when price breaks above the 20-day SMA plus 1.5x ATR (strong upward breakout), sells when price drops below the SMA minus 1.5x ATR (downward breakout). Captures large directional moves.",
        "category": "Volatility",
        "columns": [
            {"name": "atr_prev_close", "formula": "close.shift(1)"},
            {"name": "atr_tr1", "formula": "high - low"},
            {"name": "atr_tr2", "formula": "(high - atr_prev_close).abs()"},
            {"name": "atr_tr3", "formula": "(low - atr_prev_close).abs()"},
            {"name": "atr_tr", "formula": "atr_tr1.combine(atr_tr2, max).combine(atr_tr3, max)"},
            {"name": "atr", "formula": "atr_tr.rolling(14).mean()"},
            {"name": "sma_20", "formula": "close.rolling(20).mean()"},
            {"name": "upper_band", "formula": "sma_20 + 1.5 * atr"},
            {"name": "lower_band", "formula": "sma_20 - 1.5 * atr"},
        ],
        "signal_rule": "close > upper_band : 1, close < lower_band : -1, True : 0",
        "tags": ["ATR", "breakout", "volatility bands"],
    },
    {
        "id": "roc_momentum",
        "name": "ROC Momentum",
        "description": "Rate of Change momentum strategy using ROC(20). Buys when the 20-period ROC exceeds +5% (strong upward momentum), sells when it drops below -5% (strong downward momentum). Simple threshold-based approach for momentum traders.",
        "category": "Momentum",
        "columns": [
            {"name": "roc_20", "formula": "(close - close.shift(20)) / close.shift(20) * 100"},
        ],
        "signal_rule": "roc_20 > 5 : 1, roc_20 < -5 : -1, True : 0",
        "tags": ["ROC", "momentum", "threshold"],
    },
    {
        "id": "triple_ema",
        "name": "Triple EMA Trend",
        "description": "Multi-timeframe trend strategy using three EMAs (8, 21, 55). Buys when all three EMAs are aligned bullishly (fast > medium > slow), sells when aligned bearishly. The triple confirmation reduces whipsaws compared to dual-EMA crossovers.",
        "category": "Trend Following",
        "columns": [
            {"name": "ema_8", "formula": "close.ewm(span=8, adjust=False).mean()"},
            {"name": "ema_21", "formula": "close.ewm(span=21, adjust=False).mean()"},
            {"name": "ema_55", "formula": "close.ewm(span=55, adjust=False).mean()"},
        ],
        "signal_rule": "(ema_8 > ema_21) & (ema_21 > ema_55) : 1, (ema_8 < ema_21) & (ema_21 < ema_55) : -1, True : 0",
        "tags": ["EMA", "triple", "trend confirmation"],
    },
    {
        "id": "bb_rsi_combo",
        "name": "Bollinger + RSI Combo",
        "description": "Combined strategy using Bollinger Bands(20) and RSI(14) for high-confidence signals. Buys only when price is below the lower Bollinger Band AND RSI is below 35 (double oversold confirmation). Sells when price is above the upper band AND RSI is above 65.",
        "category": "Mean Reversion",
        "columns": [
            {"name": "bb_mid", "formula": "close.rolling(20).mean()"},
            {"name": "bb_std", "formula": "close.rolling(20).std()"},
            {"name": "bb_upper", "formula": "bb_mid + 2 * bb_std"},
            {"name": "bb_lower", "formula": "bb_mid - 2 * bb_std"},
            {"name": "rsi_delta", "formula": "close.diff()"},
            {"name": "rsi_gain", "formula": "rsi_delta.clip(lower=0)"},
            {"name": "rsi_loss", "formula": "-rsi_delta.clip(upper=0)"},
            {"name": "rsi_avg_gain", "formula": "rsi_gain.rolling(14).mean()"},
            {"name": "rsi_avg_loss", "formula": "rsi_loss.rolling(14).mean()"},
            {"name": "rsi_rs", "formula": "rsi_avg_gain / rsi_avg_loss"},
            {"name": "rsi", "formula": "100 - (100 / (1 + rsi_rs))"},
        ],
        "signal_rule": "(close < bb_lower) & (rsi < 35) : 1, (close > bb_upper) & (rsi > 65) : -1, True : 0",
        "tags": ["Bollinger Bands", "RSI", "dual confirmation"],
    },
]


def list_templates() -> list:
    """Return all available strategy templates."""
    return STRATEGY_TEMPLATES


def get_template(template_id: str) -> dict | None:
    """Get a single template by its ID slug."""
    for t in STRATEGY_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
