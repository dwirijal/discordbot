from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class DexAnalysisData:
    """Data model for DEX analysis results"""
    name: str
    symbol: str
    address: str
    price_usd: float
    price_native: float
    quote_symbol: str
    dex_id: str
    chain: str
    url: str
    image_url: Optional[str]
    explorer_url: Optional[str]

    signal: str
    age_hours: float
    social_count: int
    boosts: int

    market_cap: float
    liquidity_usd: float
    volume_24h: float
    turnover_ratio: float

    buy_ratio: float
    buys_count: int
    sells_count: int

    changes: Dict[str, float]

    liq_base: float
    liq_quote: float

    risk_flags: str

    color: int  # Discord embed color

@dataclass
class AnalysisResult:
    """Data model for technical analysis results"""
    symbol: str
    timeframe: str
    current_price: float
    price_change_24h: float
    volume_24h: float

    indicators: Dict[str, float]
    levels: Dict[str, any]
    signal: Dict[str, any]
    divergences: Dict[str, List]

    timestamp: any  # Discord datetime