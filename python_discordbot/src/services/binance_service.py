import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
from ..config.settings import Settings
from ..services.indicators import TechnicalIndicators, AdvancedAnalytics
from ..config.trading_config import TradingConfig

logger = logging.getLogger(__name__)

class BinanceService:
    """Service for fetching and analyzing Binance data"""

    def __init__(self, cache_service=None):
        self.settings = Settings()
        self.base_url = "https://api.binance.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache_service = cache_service

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """Fetch kline data from Binance"""
        cache_key = f"binance:klines:{symbol}:{interval}:{limit}"
        
        # Check PostgreSQL cache
        if self.cache_service:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                return pd.DataFrame(cached_data)

        url = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }

        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch klines: {response.status}")

            data = await response.json()

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'count', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ])

            # Convert types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Cache with appropriate TTL based on timeframe
            if self.cache_service:
                ttl = self._get_cache_ttl(interval)
                await self.cache_service.set(cache_key, df.to_dict('records'), ttl)

            return df

    async def get_ticker_24hr(self, symbol: str) -> Dict:
        """Get 24hr ticker statistics"""
        url = f"{self.base_url}/api/v3/ticker/24hr"
        params = {"symbol": symbol}

        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch ticker: {response.status}")
            return await response.json()

    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book depth"""
        url = f"{self.base_url}/api/v3/depth"
        params = {"symbol": symbol, "limit": limit}

        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch orderbook: {response.status}")
            return await response.json()

    async def fetch_mtfa_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for all configured timeframes"""
        tasks = []
        timeframes = TradingConfig.TIMEFRAMES
        
        for tf in timeframes:
            limit = 500
            if tf == '1d': limit = 1000
            elif tf == '1w': limit = 300
            elif tf == '1M': limit = 200
            tasks.append(self.get_klines(symbol, tf, limit))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for tf, result in zip(timeframes, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {tf} for {symbol}: {result}")
                continue
            data[tf] = result
            
        return data

    async def analyze_symbol(self, symbol: str) -> Dict:
        """Comprehensive analysis of a symbol using MTFA"""
        try:
            # Fetch MTFA data
            mtfa_data = await self.fetch_mtfa_data(symbol)
            
            if '15m' not in mtfa_data:
                raise Exception("Failed to fetch base timeframe (15m) data")

            # Get ticker for current price info
            ticker = await self.get_ticker_24hr(symbol)
            
            # We will return the raw data and ticker here. 
            # The actual analysis will be done by the SignalEngine/MTFAEngine.
            # This keeps the service focused on data fetching.
            
            return {
                'symbol': symbol,
                'mtfa_data': mtfa_data,
                'ticker': ticker,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            raise

    def _get_cache_ttl(self, interval: str) -> int:
        """Determine cache TTL based on timeframe"""
        ttl_map = {
            '1m': 30,
            '5m': 60,
            '15m': 60,
            '30m': 120,
            '1h': 120,
            '4h': 300,
            '1d': 600,
            '1w': 600,
            '1M': 600
        }
        return ttl_map.get(interval, 60)

    def generate_signal(self, analysis: Dict) -> Dict:
        """Generate trading signal based on indicators"""
        signals = []
        score = 0

        # RSI signals
        rsi = analysis.get('rsi', 50)
        if rsi < 30:
            signals.append("RSI Oversold")
            score += 2
        elif rsi > 70:
            signals.append("RSI Overbought")
            score -= 2

        # MACD signals
        macd_hist = analysis.get('macd_histogram', 0)
        if macd_hist > 0 and macd_hist > analysis.get('macd_histogram', 0):
            signals.append("MACD Bullish")
            score += 2
        elif macd_hist < 0:
            signals.append("MACD Bearish")
            score -= 2

        # Moving average signals
        current_price = analysis.get('current_price', 0)
        sma_20 = analysis.get('sma_20', current_price)
        sma_50 = analysis.get('sma_50', current_price)
        sma_200 = analysis.get('sma_200', current_price)

        if current_price > sma_20 > sma_50 > sma_200:
            signals.append("Strong Uptrend")
            score += 3
        elif current_price < sma_20 < sma_50 < sma_200:
            signals.append("Strong Downtrend")
            score -= 3

        # Bollinger Bands
        bb_position = (current_price - analysis.get('bb_lower', current_price)) / \
                     (analysis.get('bb_upper', current_price) - analysis.get('bb_lower', current_price))
        if bb_position < 0.1:
            signals.append("BB Oversold")
            score += 1
        elif bb_position > 0.9:
            signals.append("BB Overbought")
            score -= 1

        # Volume/CMF
        cmf = analysis.get('cmf', 0)
        if cmf > 0.1:
            signals.append("Strong Buying Pressure")
            score += 2
        elif cmf < -0.1:
            signals.append("Strong Selling Pressure")
            score -= 2

        # Determine overall signal
        if score >= 4:
            overall_signal = "STRONG BUY"
            confidence = min(95, score * 20)
        elif score >= 2:
            overall_signal = "BUY"
            confidence = min(80, score * 20)
        elif score >= -1:
            overall_signal = "HOLD"
            confidence = 50
        elif score >= -3:
            overall_signal = "SELL"
            confidence = min(80, abs(score) * 20)
        else:
            overall_signal = "STRONG SELL"
            confidence = min(95, abs(score) * 20)

        return {
            'signal': overall_signal,
            'confidence': confidence,
            'score': score,
            'reasons': signals[:5]  # Top 5 reasons
        }