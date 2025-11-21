from fastapi import FastAPI, Request, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
import json
import uvicorn
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import aiofiles
import os
from pathlib import Path

# Add parent to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.services.binance_service import BinanceService
from src.services.signal_engine import SignalEngine
from src.services.cache_service import CacheService
from src.config.settings import Settings
from src.config.trading_config import TradingConfig
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Crypto Trading Bot Dashboard",
    description="Real-time monitoring dashboard for crypto trading bot",
    version="1.0.0"
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Security
security = HTTPBasic()
settings = Settings()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for services
cache_service = None
binance_service = None
signal_engine = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection might be closed
                self.active_connections.remove(connection)

manager = ConnectionManager()

async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Simple authentication (in production, use proper auth)"""
    # For demo, accept any credentials
    # In production, validate against database
    return credentials.username

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global cache_service, binance_service, signal_engine

    # Initialize services
    from src.utils.init_db import initialize_database
    cache_service = await initialize_database(settings)
    binance_service = BinanceService(cache_service)
    signal_engine = SignalEngine()

    logger.info("Web dashboard started successfully")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = Depends(get_current_user)):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Crypto Trading Bot Dashboard",
        "username": username,
        "symbols": TradingConfig.SYMBOLS,
        "timeframes": TradingConfig.TIMEFRAMES
    })

@app.get("/signals")
async def get_signals(username: str = Depends(get_current_user)):
    """Get recent trading signals"""
    try:
        # Get signals from cache or database
        signals = []

        # For demo, generate some sample signals
        for symbol in TradingConfig.SYMBOLS[:5]:
            signal = {
                "symbol": symbol,
                "type": "BUY" if hash(symbol) % 2 else "SELL",
                "confidence": (hash(symbol) % 30) + 70,
                "entry_price": 45000 + (hash(symbol) % 10000),
                "stop_loss": 44000 + (hash(symbol) % 8000),
                "take_profit": 47000 + (hash(symbol) % 12000),
                "timestamp": datetime.now().isoformat(),
                "reasons": ["RSI Oversold", "MACD Bullish", "Volume Spike"]
            }
            signals.append(signal)

        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
        return {"signals": []}

@app.get("/market/{symbol}")
async def get_market_data(symbol: str, username: str = Depends(get_current_user)):
    """Get market data for a symbol"""
    try:
        # Fetch data from Binance
        async with binance_service as bs:
            mtfa_data = await bs.fetch_mtfa_data(symbol + "USDT")

        # Process data for charts
        chart_data = {}
        for tf, df in mtfa_data.items():
            if df is not None and not df.empty:
                chart_data[tf] = [
                    {
                        "timestamp": int(row['timestamp'].timestamp() * 1000),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": float(row['volume'])
                    }
                    for _, row in df.tail(100).iterrows()
                ]

        # Get current signal
        signal = signal_engine.analyze_market(symbol, mtfa_data)

        return {
            "symbol": symbol,
            "chart_data": chart_data,
            "signal": {
                "type": signal.type,
                "confidence": signal.confidence,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "risk_reward_ratio": signal.risk_reward_ratio
            }
        }
    except Exception as e:
        logger.error(f"Error fetching market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance")
async def get_performance(username: str = Depends(get_current_user)):
    """Get bot performance metrics"""
    try:
        # Sample performance data
        performance = {
            "total_signals": 156,
            "win_rate": 68.5,
            "total_pnl": 12.5,
            "current_positions": 5,
            "daily_pnl": [
                {"date": "2024-01-20", "pnl": 2.5},
                {"date": "2024-01-19", "pnl": -1.2},
                {"date": "2024-01-18", "pnl": 3.8},
                {"date": "2024-01-17", "pnl": 0.5},
                {"date": "2024-01-16", "pnl": 4.2}
            ],
            "signal_distribution": {
                "BUY": 85,
                "SELL": 45,
                "NEUTRAL": 26
            },
            "symbol_performance": [
                {"symbol": "BTC/USDT", "pnl": 8.5, "signals": 45},
                {"symbol": "ETH/USDT", "pnl": 5.2, "signals": 38},
                {"symbol": "SOL/USDT", "pnl": -2.1, "signals": 32},
                {"symbol": "BNB/USDT", "pnl": 3.4, "signals": 25},
                {"symbol": "AVAX/USDT", "pnl": -2.5, "signals": 16}
            ]
        }

        return performance
    except Exception as e:
        logger.error(f"Error fetching performance: {e}")
        return {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send real-time updates
            update = {
                "type": "price_update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "BTC/USDT": {
                        "price": 45000 + (hash(datetime.now().isoformat()) % 1000),
                        "change": ((hash(datetime.now().isoformat()) % 200) - 100) / 100
                    },
                    "ETH/USDT": {
                        "price": 2500 + (hash(datetime.now().isoformat()) % 500),
                        "change": ((hash(datetime.now().isoformat()) % 150) - 75) / 100
                    }
                }
            }

            await manager.send_personal_message(json.dumps(update), websocket)
            await asyncio.sleep(2)  # Update every 2 seconds

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "binance": "connected" if binance_service else "disconnected",
            "cache": "connected" if cache_service else "disconnected",
            "signal_engine": "active" if signal_engine else "inactive"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )