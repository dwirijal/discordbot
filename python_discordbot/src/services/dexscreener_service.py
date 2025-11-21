import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class DexScreenerService:
    """Service for fetching DexScreener data"""

    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def is_contract_address(self, query: str) -> bool:
        """Check if query is a contract address"""
        # Ethereum/BSC/Polygon addresses
        eth_pattern = r'^0x[a-fA-F0-9]{40}$'
        # Solana addresses
        sol_pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'

        return bool(re.match(eth_pattern, query) or re.match(sol_pattern, query))

    async def get_token_data(self, address: Optional[str] = None,
                           symbol: Optional[str] = None) -> Optional[Dict]:
        """Fetch token data from DexScreener"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            if address:
                url = f"{self.base_url}/dex/tokens/{address}"
            elif symbol:
                url = f"{self.base_url}/dex/search?q={symbol}"
            else:
                raise ValueError("Either address or symbol must be provided")

            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"DexScreener API error: {response.status}")
                    return None

                data = await response.json()
                return data

        except asyncio.TimeoutError:
            logger.error("DexScreener API timeout")
            return None
        except Exception as e:
            logger.error(f"Error fetching DexScreener data: {str(e)}")
            return None

    async def get_pairs_by_chain(self, chain_id: str, limit: int = 10) -> Optional[List[Dict]]:
        """Get top pairs by chain"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = f"{self.base_url}/dex/pairs/{chain_id}"
            async with self.session.get(url, params={"limit": limit}) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                return data.get('pairs', [])

        except Exception as e:
            logger.error(f"Error fetching pairs by chain: {str(e)}")
            return None

    async def get_most_active_pairs(self, limit: int = 20) -> Optional[List[Dict]]:
        """Get most active pairs across all chains"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # DexScreener doesn't have a direct endpoint for this
            # We'll use the ranking endpoint
            url = "https://api.dexscreener.com/latest/dex/rankings/volume"
            async with self.session.get(url, params={"limit": limit}) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                return data.get('rankings', [])

        except Exception as e:
            logger.error(f"Error fetching most active pairs: {str(e)}")
            return None

    async def analyze_token(self, query: str) -> Dict:
        """Comprehensive token analysis"""
        is_address = self.is_contract_address(query)

        # Fetch data
        data = await self.get_token_data(
            address=query if is_address else None,
            symbol=query.upper() if not is_address else None
        )

        if not data or not data.get('pairs'):
            return {
                'error': True,
                'message': f"Token not found: {query}"
            }

        pairs = data['pairs']

        # Filter for quality pairs
        quality_pairs = []
        for pair in pairs:
            liquidity = pair.get('liquidity', {}).get('usd', 0)
            volume_24h = pair.get('volume', {}).get('h24', 0)

            # Minimum requirements
            if liquidity >= 1000 and volume_24h >= 1000:
                quality_pairs.append(pair)

        if not quality_pairs:
            # Fallback to any liquid pair
            quality_pairs = [p for p in pairs if p.get('liquidity', {}).get('usd', 0) > 100]

        if not quality_pairs:
            return {
                'error': True,
                'message': "No liquid pairs found"
            }

        # Sort by liquidity
        quality_pairs.sort(key=lambda p: p.get('liquidity', {}).get('usd', 0), reverse=True)
        best_pair = quality_pairs[0]

        # Extract token info
        base_token = best_pair.get('baseToken', {})
        quote_token = best_pair.get('quoteToken', {})

        # Basic metrics
        price_usd = float(best_pair.get('priceUsd', 0))
        price_native = float(best_pair.get('priceNative', 0))

        # Liquidity metrics
        liquidity = best_pair.get('liquidity', {})
        liq_usd = float(liquidity.get('usd', 0))
        liq_base = float(liquidity.get('base', 0))
        liq_quote = float(liquidity.get('quote', 0))

        # Volume metrics
        volume = best_pair.get('volume', {})
        vol_24h = float(volume.get('h24', 0))
        vol_6h = float(volume.get('h6', 0))
        vol_1h = float(volume.get('h1', 0))
        vol_5m = float(volume.get('m5', 0))

        # Transaction metrics
        txns = best_pair.get('txns', {})
        txns_24h = txns.get('h24', {})
        buys_24h = txns_24h.get('buys', 0)
        sells_24h = txns_24h.get('sells', 0)
        total_txns_24h = buys_24h + sells_24h
        buy_ratio = (buys_24h / total_txns_24h * 100) if total_txns_24h > 0 else 50

        # Price changes
        price_change = best_pair.get('priceChange', {})

        # Market metrics
        market_cap = float(best_pair.get('marketCap', 0))
        fdv = float(best_pair.get('fdv', 0))

        # Calculate additional metrics
        turnover_ratio = (vol_24h / market_cap * 100) if market_cap > 0 else 0

        # Liquidity score (0-100)
        liquidity_score = min(100, (liq_usd / 10000) * 100) if liq_usd > 0 else 0

        # Volume consistency score
        volume_scores = []
        if vol_1h > 0: volume_scores.append(min(100, (vol_1h / 1000) * 50))
        if vol_6h > 0: volume_scores.append(min(100, (vol_6h / 6000) * 50))
        if vol_24h > 0: volume_scores.append(min(100, (vol_24h / 24000) * 50))
        volume_score = sum(volume_scores) / len(volume_scores) if volume_scores else 0

        # Transaction score
        txn_score = min(100, (total_txns_24h / 100) * 100)

        # Buy pressure score
        buy_pressure_score = buy_ratio

        # Age score (newer tokens get higher score)
        created_at = best_pair.get('pairCreatedAt', 0)
        age_hours = (datetime.now().timestamp() * 1000 - created_at) / (1000 * 60 * 60)
        age_score = max(0, 100 - age_hours)  # Deduct 1 point per hour

        # Social score
        info = best_pair.get('info', {})
        socials = info.get('socials', [])
        social_score = min(100, len(socials) * 25)

        # Boost score
        boosts = best_pair.get('boosts', {})
        active_boosts = boosts.get('active', 0)
        boost_score = min(100, active_boosts * 20)

        # Risk assessment
        risk_factors = {
            'low_liquidity': liq_usd < 5000,
            'low_volume': vol_24h < 10000,
            'high_volatility': abs(price_change.get('h24', 0)) > 50,
            'no_socials': len(socials) == 0,
            'new_token': age_hours < 24,
            'sell_pressure': buy_ratio < 40
        }

        risk_score = sum(risk_factors.values()) * 16.67  # 6 factors, max 100

        # Overall score
        overall_score = (
            liquidity_score * 0.25 +
            volume_score * 0.20 +
            txn_score * 0.15 +
            buy_pressure_score * 0.20 +
            social_score * 0.10 +
            boost_score * 0.10
        )

        # Generate signal
        if overall_score >= 75 and risk_score < 35:
            signal = "STRONG BUY 🚀"
        elif overall_score >= 60 and risk_score < 50:
            signal = "BUY 🟢"
        elif overall_score >= 40:
            signal = "HOLD ⚪"
        elif risk_score >= 70:
            signal = "AVOID ☠️"
        else:
            signal = "SELL 🔴"

        # Scam detection
        scam_flags = []
        if liq_usd < 1000:
            scam_flags.append("💀 Extremely Low Liquidity")
        if buy_ratio < 20 and total_txns_24h > 100:
            scam_flags.append("🔴 Heavy Selling")
        if price_change.get('h5', 0) < -90:
            scam_flags.append("📉 Rug Pull Pattern")
        if len(socials) == 0 and market_cap > 100000:
            scam_flags.append("👤 No Social Presence")

        # Top holders check (if available)
        top_holders = best_pair.get('holders', {})
        if top_holders:
            holder_concentration = top_holders.get('top10', 0)
            if holder_concentration > 80:
                scam_flags.append("🎯 High Holder Concentration")

        return {
            'token': {
                'name': base_token.get('name', 'Unknown'),
                'symbol': base_token.get('symbol', 'UNK'),
                'address': base_token.get('address', ''),
                'image_url': info.get('imageUrl', '')
            },
            'price': {
                'usd': price_usd,
                'native': price_native,
                'symbol': quote_token.get('symbol', 'QUOTE'),
                'changes': price_change
            },
            'market': {
                'market_cap': market_cap,
                'fdv': fdv,
                'liquidity': {
                    'usd': liq_usd,
                    'base': liq_base,
                    'quote': liq_quote,
                    'score': liquidity_score
                },
                'volume': {
                    '24h': vol_24h,
                    '6h': vol_6h,
                    '1h': vol_1h,
                    '5m': vol_5m,
                    'score': volume_score
                },
                'turnover_ratio': turnover_ratio
            },
            'transactions': {
                'buys_24h': buys_24h,
                'sells_24h': sells_24h,
                'total_24h': total_txns_24h,
                'buy_ratio': buy_ratio,
                'score': txn_score
            },
            'metadata': {
                'chain': best_pair.get('chainId', 'Unknown'),
                'dex': best_pair.get('dexId', 'Unknown'),
                'pair_address': best_pair.get('pairAddress', ''),
                'url': best_pair.get('url', ''),
                'created_at': created_at,
                'age_hours': age_hours,
                'socials': socials,
                'boosts': active_boosts,
                'explorer_url': self._get_explorer_url(
                    best_pair.get('chainId', ''),
                    base_token.get('address', '')
                )
            },
            'scores': {
                'overall': round(overall_score, 2),
                'liquidity': round(liquidity_score, 2),
                'volume': round(volume_score, 2),
                'transactions': round(txn_score, 2),
                'social': round(social_score, 2),
                'boosts': round(boost_score, 2),
                'risk': round(risk_score, 2)
            },
            'signal': signal,
            'scam_flags': scam_flags,
            'recommendation': self._generate_recommendation(
                overall_score, risk_score, signal, scam_flags
            )
        }

    def _get_explorer_url(self, chain_id: str, address: str) -> str:
        """Get appropriate explorer URL for the chain"""
        explorers = {
            'ethereum': f'https://etherscan.io/token/{address}',
            'bsc': f'https://bscscan.com/token/{address}',
            'polygon': f'https://polygonscan.com/token/{address}',
            'arbitrum': f'https://arbiscan.io/token/{address}',
            'avalanche': f'https://snowtrace.io/token/{address}',
            'fantom': f'https://ftmscan.io/token/{address}',
            'solana': f'https://solscan.io/token/{address}',
            'base': f'https://basescan.org/token/{address}',
            'optimism': f'https://optimistic.etherscan.io/token/{address}',
            'cronos': f'https://cronoscan.com/token/{address}',
            'celo': f'https://celoscan.io/token/{address}',
            'aurora': f'https://aurorascan.dev/token/{address}'
        }
        return explorers.get(chain_id.lower(), f'https://etherscan.io/token/{address}')

    def _generate_recommendation(self, overall_score: float, risk_score: float,
                                signal: str, scam_flags: List[str]) -> str:
        """Generate trading recommendation"""
        if scam_flags:
            return "⚠️ HIGH RISK - Multiple red flags detected. DYOR before investing."

        if signal == "STRONG BUY 🚀":
            if overall_score > 85:
                return "✅ Excellent fundamentals with strong momentum. Consider position sizing."
            else:
                return "🟢 Good entry opportunity with decent volume."
        elif signal == "BUY 🟢":
            return "🟡 Moderate bullish signals. Wait for confirmation."
        elif signal == "HOLD ⚪":
            return "⏸️ Neutral signals. Wait for better entry/exit."
        elif signal == "SELL 🔴":
            return "🔴 Consider taking profits or cutting losses."
        else:  # AVOID
            return "☠️ HIGH RISK - Avoid or extremely small position if you must."