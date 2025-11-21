import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent / "python_discordbot"))

from src.services.binance_service import BinanceService
from src.services.polymarket_service import PolymarketService
from src.services.gemini_processor import GeminiProcessor
from src.services.signal_engine import SignalEngine
from src.config.trading_config import TradingConfig

async def main():
    print("🔍 Starting Verification...")
    load_dotenv()
    
    # Check Environment
    print(f"Checking API Keys...")
    if os.getenv("GEMINI_API_KEY"):
        print("✅ GEMINI_API_KEY found")
    else:
        print("⚠️ GEMINI_API_KEY not found (Gemini analysis will be skipped/mocked)")

    # Initialize Services
    print("\nInitializing Services...")
    try:
        binance = BinanceService()
        polymarket = PolymarketService()
        gemini = GeminiProcessor()
        engine = SignalEngine()
        print("✅ Services Initialized")
    except Exception as e:
        print(f"❌ Service Initialization Failed: {e}")
        return

    # Test Data Fetching
    symbol = "BTC/USDT"
    print(f"\nTesting Analysis for {symbol}...")
    
    try:
        async with binance as bs, polymarket as ps:
            # 1. Polymarket
            print("Fetching Polymarket events...")
            events = await ps.get_events()
            print(f"✅ Fetched {len(events)} events")
            
            # 2. Gemini
            print("Running Gemini Analysis...")
            gemini_analysis = await gemini.analyze_polymarket_events(events)
            print(f"✅ Gemini Result: {gemini_analysis.get('sentiment')} (Score: {gemini_analysis.get('score')})")
            
            # 3. Binance MTFA
            print("Fetching Binance MTFA Data...")
            mtfa_data = await bs.fetch_mtfa_data(symbol)
            print(f"✅ Fetched timeframes: {list(mtfa_data.keys())}")
            
            # 4. Signal Engine
            print("Generating Signal...")
            signal = engine.analyze_market(symbol, mtfa_data, gemini_analysis)
            print(f"\n🎉 SIGNAL GENERATED:")
            print(f"Type: {signal.type}")
            print(f"Confidence: {signal.confidence}")
            print(f"Entry: {signal.entry_price}")
            print(f"Reasons: {signal.reasons}")
            
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
