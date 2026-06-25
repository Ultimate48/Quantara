"""
Predefined indicator shortcuts that expand into column definition chains.
Usage: --indicator RSI,14 expands into the full RSI column chain with period=14.

Each preset is a function that takes parameters and returns a list of
{"name": str, "formula": str} dicts matching the strategy column format.
"""


def _rsi(period: int = 14) -> list:
    """RSI (Relative Strength Index) with configurable period."""
    return [
        {"name": "rsi_delta", "formula": "close.diff()"},
        {"name": "rsi_gain", "formula": "rsi_delta.clip(lower=0)"},
        {"name": "rsi_loss", "formula": "-rsi_delta.clip(upper=0)"},
        {"name": f"rsi_avg_gain", "formula": f"rsi_gain.rolling({period}).mean()"},
        {"name": f"rsi_avg_loss", "formula": f"rsi_loss.rolling({period}).mean()"},
        {"name": "rsi_rs", "formula": "rsi_avg_gain / rsi_avg_loss"},
        {"name": "rsi", "formula": "100 - (100 / (1 + rsi_rs))"},
    ]


def _sma(period: int = 20) -> list:
    """Simple Moving Average."""
    return [
        {"name": f"sma_{period}", "formula": f"close.rolling({period}).mean()"},
    ]


def _ema(period: int = 12) -> list:
    """Exponential Moving Average."""
    return [
        {"name": f"ema_{period}", "formula": f"close.ewm(span={period}, adjust=False).mean()"},
    ]


def _bb(period: int = 20) -> list:
    """Bollinger Bands (middle, upper, lower)."""
    return [
        {"name": "bb_mid", "formula": f"close.rolling({period}).mean()"},
        {"name": "bb_std", "formula": f"close.rolling({period}).std()"},
        {"name": "bb_upper", "formula": "bb_mid + 2 * bb_std"},
        {"name": "bb_lower", "formula": "bb_mid - 2 * bb_std"},
    ]


def _macd(fast: int = 12, slow: int = 26, signal: int = 9) -> list:
    """MACD (Moving Average Convergence Divergence)."""
    return [
        {"name": "macd_fast", "formula": f"close.ewm(span={fast}, adjust=False).mean()"},
        {"name": "macd_slow", "formula": f"close.ewm(span={slow}, adjust=False).mean()"},
        {"name": "macd_line", "formula": "macd_fast - macd_slow"},
        {"name": "macd_signal", "formula": f"macd_line.ewm(span={signal}, adjust=False).mean()"},
        {"name": "macd_hist", "formula": "macd_line - macd_signal"},
    ]


def _atr(period: int = 14) -> list:
    """Average True Range — requires high, low, close columns."""
    return [
        {"name": "atr_prev_close", "formula": "close.shift(1)"},
        {"name": "atr_tr1", "formula": "high - low"},
        {"name": "atr_tr2", "formula": "(high - atr_prev_close).abs()"},
        {"name": "atr_tr3", "formula": "(low - atr_prev_close).abs()"},
        # True range = max of the three components; use pandas max across columns
        {"name": "atr_tr", "formula": "atr_tr1.combine(atr_tr2, max).combine(atr_tr3, max)"},
        {"name": f"atr", "formula": f"atr_tr.rolling({period}).mean()"},
    ]


def _roc(period: int = 20) -> list:
    """Rate of Change (percentage)."""
    return [
        {"name": f"roc_{period}", "formula": f"(close - close.shift({period})) / close.shift({period}) * 100"},
    ]


# Registry mapping shorthand names to their generator functions
INDICATOR_REGISTRY = {
    "RSI":  {"fn": _rsi,  "params": ["period"],              "defaults": [14],       "description": "Relative Strength Index"},
    "SMA":  {"fn": _sma,  "params": ["period"],              "defaults": [20],       "description": "Simple Moving Average"},
    "EMA":  {"fn": _ema,  "params": ["period"],              "defaults": [12],       "description": "Exponential Moving Average"},
    "BB":   {"fn": _bb,   "params": ["period"],              "defaults": [20],       "description": "Bollinger Bands (mid/upper/lower)"},
    "MACD": {"fn": _macd, "params": ["fast", "slow", "signal"], "defaults": [12, 26, 9], "description": "MACD line, signal, histogram"},
    "ATR":  {"fn": _atr,  "params": ["period"],              "defaults": [14],       "description": "Average True Range"},
    "ROC":  {"fn": _roc,  "params": ["period"],              "defaults": [20],       "description": "Rate of Change (%)"},
}


def expand_indicator(indicator_str: str) -> list:
    """
    Parse an indicator string like 'RSI,14' or 'MACD,12,26,9' and return
    the expanded column definitions list.

    Format: NAME[,param1[,param2[,param3]]]
    If params omitted, uses defaults from registry.
    """
    parts = [p.strip() for p in indicator_str.split(",")]
    name = parts[0].upper()

    if name not in INDICATOR_REGISTRY:
        available = ", ".join(sorted(INDICATOR_REGISTRY.keys()))
        raise ValueError(f"Unknown indicator '{name}'. Available: {available}")

    entry = INDICATOR_REGISTRY[name]
    fn = entry["fn"]
    param_names = entry["params"]
    defaults = entry["defaults"]

    # Parse provided parameters, falling back to defaults
    args = []
    for i, param_name in enumerate(param_names):
        if i + 1 < len(parts):
            try:
                args.append(int(parts[i + 1]))
            except ValueError:
                raise ValueError(f"Invalid value for {name} parameter '{param_name}': '{parts[i + 1]}' (expected integer)")
        else:
            args.append(defaults[i])

    return fn(*args)


def list_indicators() -> list:
    """Return a list of available indicator presets with their descriptions."""
    result = []
    for name, entry in sorted(INDICATOR_REGISTRY.items()):
        params_str = ",".join(str(d) for d in entry["defaults"])
        result.append({
            "name": name,
            "usage": f"{name},{params_str}" if params_str else name,
            "params": entry["params"],
            "defaults": entry["defaults"],
            "description": entry["description"],
        })
    return result
