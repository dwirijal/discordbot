import aiohttp
import logging
from typing import List, Dict, Optional
from ..config.trading_config import TradingConfig
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class PolymarketService:
    """Service for fetching data from Polymarket Gamma API"""
    
    BASE_URL = "https://gamma-api.polymarket.com" # This will be replaced by self.base_url

    def __init__(self, cache_service=None): # Modified signature
        self.settings = Settings() # Added
        self.base_url = self.settings.POLYMARKET_API_URL # Modified
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache_service = cache_service # Added

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_events(self) -> List[Dict]: # Modified signature
        """Fetch top crypto-related events from Polymarket""" # Modified docstring
        # Generate cache key from keywords
        keywords_str = ",".join(sorted(TradingConfig.POLYMARKET_KEYWORDS))
        cache_key = f"polymarket:events:{self.cache_service.hash_data(keywords_str) if self.cache_service else keywords_str}"
        
        # Check cache
        if self.cache_service:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT: Polymarket events")
                return cached_data
        
        try:
            events = []
            for keyword in TradingConfig.POLYMARKET_KEYWORDS: # Modified iteration
                try:
                    url = f"{self.base_url}/events" # Modified URL
                    params = {
                        "limit": 10,
                        "offset": 0, # Added offset
                        "tag": keyword # Modified parameter
                    }
                    
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            events.extend(data[:5])  # Top 5 per keyword # Modified data processing
                        else:
                            logger.warning(f"Failed to fetch Polymarket events for {keyword}: {response.status}")
                except Exception as e:
                    logger.error(f"Error fetching Polymarket events for {keyword}: {e}")
            
            # Cache for 5 minutes
            if self.cache_service and events:
                await self.cache_service.set(cache_key, events, 300)
            
            logger.info(f"✅ Fetched {len(events)} events") # Modified log message
            return events
            
        except Exception as e:
            logger.error(f"Error fetching Polymarket events: {e}") # Modified log message
            return []

    async def get_market_data(self, condition_id: str) -> Dict:
        """Get specific market data"""
        # Implementation for specific market details if needed
        pass
