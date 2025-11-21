import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from ..config.trading_config import TradingConfig
from ..services.indicators import TechnicalIndicators, AdvancedAnalytics

logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    symbol: str
    type: str  # BUY, SELL, NEUTRAL
    confidence: str  # HIGH, MEDIUM, LOW
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    reasons: List[str]
    timestamp: str
    mtfa_analysis: Dict[str, str]  # Summary of analysis per timeframe

class SignalEngine:
    """Engine for Multi-Timeframe Analysis and Signal Generation"""

    def __init__(self):
        self.config = TradingConfig()

    def analyze_market(self, symbol: str, mtfa_data: Dict[str, pd.DataFrame], gemini_analysis: Dict) -> TradeSignal:
        """
        Perform top-down analysis from Monthly to 15m.
        Returns a TradeSignal.
        """
        reasons = []
        mtfa_summary = {}
        
        # 1. Monthly/Weekly - Main Trend
        monthly_trend = self._analyze_trend(mtfa_data.get('1M'), '1M')
        weekly_trend = self._analyze_trend(mtfa_data.get('1w'), '1w')
        
        mtfa_summary['1M'] = monthly_trend
        mtfa_summary['1w'] = weekly_trend
        
        main_trend = "NEUTRAL"
        if monthly_trend == "BULLISH" and weekly_trend == "BULLISH":
            main_trend = "BULLISH"
        elif monthly_trend == "BEARISH" and weekly_trend == "BEARISH":
            main_trend = "BEARISH"
            
        reasons.append(f"Main Trend (M/W): {main_trend}")

        # 2. Daily - Momentum Setup
        daily_setup = self._analyze_momentum(mtfa_data.get('1d'), '1d')
        mtfa_summary['1d'] = daily_setup
        
        if main_trend == "BULLISH" and daily_setup != "BULLISH":
            return self._create_neutral_signal(symbol, reasons, mtfa_summary)
        if main_trend == "BEARISH" and daily_setup != "BEARISH":
            return self._create_neutral_signal(symbol, reasons, mtfa_summary)

        # 3. 4h/1h - Confirmation
        h4_conf = self._analyze_momentum(mtfa_data.get('4h'), '4h')
        h1_conf = self._analyze_momentum(mtfa_data.get('1h'), '1h')
        mtfa_summary['4h'] = h4_conf
        mtfa_summary['1h'] = h1_conf
        
        if main_trend == "BULLISH" and (h4_conf != "BULLISH" or h1_conf != "BULLISH"):
             return self._create_neutral_signal(symbol, reasons, mtfa_summary)
        if main_trend == "BEARISH" and (h4_conf != "BEARISH" or h1_conf != "BEARISH"):
             return self._create_neutral_signal(symbol, reasons, mtfa_summary)

        # 4. 15m - Entry Timing
        m15_entry = self._analyze_entry(mtfa_data.get('15m'), main_trend)
        mtfa_summary['15m'] = m15_entry['status']
        
        if m15_entry['status'] != "READY":
             return self._create_neutral_signal(symbol, reasons, mtfa_summary)
             
        # 5. Risk Calculation
        current_price = mtfa_data['15m']['close'].iloc[-1]
        risk_calc = self._calculate_risk(current_price, m15_entry, main_trend, mtfa_data['15m'])
        
        if risk_calc['rr_ratio'] < self.config.RISK['MIN_RISK_REWARD_RATIO']:
            reasons.append(f"Poor R:R ({risk_calc['rr_ratio']:.2f})")
            return self._create_neutral_signal(symbol, reasons, mtfa_summary)

        # 6. Final Validation with Gemini
        sentiment_score = gemini_analysis.get('score', 0)
        if main_trend == "BULLISH" and sentiment_score < -2:
             reasons.append(f"Sentiment Divergence: {gemini_analysis.get('sentiment')}")
             # Reduce confidence or invalidate? Let's reduce confidence for now
             confidence = "LOW"
        elif main_trend == "BEARISH" and sentiment_score > 2:
             reasons.append(f"Sentiment Divergence: {gemini_analysis.get('sentiment')}")
             confidence = "LOW"
        else:
            confidence = "HIGH"
            
        reasons.append(f"Gemini Sentiment: {gemini_analysis.get('sentiment')} ({sentiment_score})")

        return TradeSignal(
            symbol=symbol,
            type="BUY" if main_trend == "BULLISH" else "SELL",
            confidence=confidence,
            entry_price=current_price,
            stop_loss=risk_calc['stop_loss'],
            take_profit=risk_calc['take_profit'],
            risk_reward_ratio=risk_calc['rr_ratio'],
            reasons=reasons,
            timestamp=pd.Timestamp.now().isoformat(),
            mtfa_analysis=mtfa_summary
        )

    def _analyze_trend(self, df: pd.DataFrame, timeframe: str) -> str:
        if df is None or df.empty: return "NEUTRAL"
        closes = df['close'].values
        ma_fast = TechnicalIndicators.sma(closes, 50)[-1]
        ma_slow = TechnicalIndicators.sma(closes, 200)[-1]
        
        if closes[-1] > ma_fast > ma_slow: return "BULLISH"
        if closes[-1] < ma_fast < ma_slow: return "BEARISH"
        return "NEUTRAL"

    def _analyze_momentum(self, df: pd.DataFrame, timeframe: str) -> str:
        if df is None or df.empty: return "NEUTRAL"
        closes = df['close'].values
        rsi = TechnicalIndicators.rsi(closes, 14)[-1]
        macd, signal, _ = TechnicalIndicators.macd(closes)
        
        bullish_score = 0
        if rsi > 50: bullish_score += 1
        if macd[-1] > signal[-1]: bullish_score += 1
        
        if bullish_score == 2: return "BULLISH"
        if bullish_score == 0: return "BEARISH"
        return "NEUTRAL"

    def _analyze_entry(self, df: pd.DataFrame, trend: str) -> Dict:
        if df is None or df.empty: return {"status": "WAIT"}
        closes = df['close'].values
        rsi = TechnicalIndicators.rsi(closes, 14)[-1]
        
        # Simple pullback entry logic
        if trend == "BULLISH":
            if rsi < 40: return {"status": "READY", "type": "PULLBACK"} # Oversold in uptrend
            if rsi > 60: return {"status": "WAIT"} # Don't buy top
        elif trend == "BEARISH":
            if rsi > 60: return {"status": "READY", "type": "PULLBACK"} # Overbought in downtrend
            if rsi < 40: return {"status": "WAIT"} # Don't sell bottom
            
        return {"status": "READY"} # Default for now if confirmed by higher TFs

    def _calculate_risk(self, entry: float, entry_signal: Dict, trend: str, df: pd.DataFrame) -> Dict:
        atr = TechnicalIndicators.atr(df['high'].values, df['low'].values, df['close'].values, 14)[-1]
        multiplier = self.config.RISK['DEFAULT_STOP_LOSS_ATR_MULTIPLIER']
        
        if trend == "BULLISH":
            stop_loss = entry - (atr * multiplier)
            take_profit = entry + (atr * multiplier * 2) # 1:2 target
        else:
            stop_loss = entry + (atr * multiplier)
            take_profit = entry - (atr * multiplier * 2)
            
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr = reward / risk if risk > 0 else 0
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rr_ratio": rr
        }

    def _create_neutral_signal(self, symbol: str, reasons: List[str], mtfa_summary: Dict) -> TradeSignal:
        return TradeSignal(
            symbol=symbol,
            type="NEUTRAL",
            confidence="LOW",
            entry_price=0,
            stop_loss=0,
            take_profit=0,
            risk_reward_ratio=0,
            reasons=reasons,
            timestamp=pd.Timestamp.now().isoformat(),
            mtfa_analysis=mtfa_summary
        )
