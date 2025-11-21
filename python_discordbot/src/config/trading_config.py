from typing import Dict, List, Any

class TradingConfig:
    # Trading Pairs
    SYMBOLS: List[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    # Timeframes for MTFA
    TIMEFRAMES: List[str] = ["1M", "1w", "1d", "4h", "1h", "15m"]
    
    # Indicator Parameters
    INDICATORS: Dict[str, Any] = {
        "RSI_PERIOD": 14,
        "RSI_OVERBOUGHT": 70,
        "RSI_OVERSOLD": 30,
        "MACD_FAST": 12,
        "MACD_SLOW": 26,
        "MACD_SIGNAL": 9,
        "BB_PERIOD": 20,
        "BB_STD_DEV": 2,
        "MA_FAST": [10, 20],
        "MA_MEDIUM": [50],
        "MA_SLOW": [100, 200],
        "VOLUME_SPIKE_THRESHOLD": 2.0  # 2x average volume
    }
    
    # Risk Management
    RISK: Dict[str, Any] = {
        "MIN_RISK_REWARD_RATIO": 2.0,
        "MAX_RISK_PER_TRADE_PERCENT": 1.0,  # 1% of account
        "DEFAULT_STOP_LOSS_ATR_MULTIPLIER": 1.5,
    }
    
    # Gemini / Polymarket
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    POLYMARKET_KEYWORDS: List[str] = ["crypto", "bitcoin", "ethereum", "fed", "interest rate", "inflation"]

    # Scheduler
    ANALYSIS_INTERVAL_MINUTES: int = 15
