import os
import logging
import google.generativeai as genai
from typing import List, Dict
from ..config.trading_config import TradingConfig
import json # Added import for json

logger = logging.getLogger(__name__)

class GeminiProcessor:
    """Service to process market data using Gemini 2.0"""

    def __init__(self, cache_service=None):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model_name = TradingConfig.GEMINI_MODEL
        self.cache_service = cache_service
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables")
            self.model = None

    async def analyze_polymarket_events(self, events: List[Dict]) -> Dict:
        """Analyze Polymarket events using Gemini 2.0"""
        # Generate cache key from events
        events_hash = self.cache_service.hash_data(events) if self.cache_service else str(hash(str(events)))
        cache_key = f"gemini:sentiment:{events_hash}"
        
        # Check cache
        if self.cache_service:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT: Gemini sentiment")
                return cached_data
        
        if not self.model or not events:
            return {"sentiment": "NEUTRAL", "score": 0, "summary": "No data available"}
        
        try:
            # Prepare events summary
            events_text = "\n".join([
                f"- {event.get('title', 'Unknown')}: {event.get('description', 'N/A')[:100]}"
                for event in events[:10]
            ])
            
            prompt = f"""Analyze the following cryptocurrency market events and provide:
1. Overall market sentiment (BULLISH, BEARISH, or NEUTRAL)
2. Sentiment score from -10 (very bearish) to +10 (very bullish)
3. Brief summary (max 100 words)

Events:
{events_text}

Respond in JSON format:
{{
  "sentiment": "BULLISH/BEARISH/NEUTRAL",
  "score": <number>,
  "summary": "<text>"
}}"""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Cache for 10 minutes
            if self.cache_service:
                await self.cache_service.set(cache_key, result, 600)
            
            logger.info(f"✅ Gemini Result: {result['sentiment']} (Score: {result['score']})")
            return result
            
        except Exception as e:
            logger.error(f"Error in Gemini analysis: {e}")
            return {"sentiment": "NEUTRAL", "score": 0, "summary": "Analysis failed"}
