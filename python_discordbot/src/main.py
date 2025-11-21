import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.binance_service import BinanceService
from src.services.dexscreener_service import DexScreenerService
from src.services.polymarket_service import PolymarketService
from src.services.gemini_processor import GeminiProcessor
from src.services.signal_engine import SignalEngine
from src.services.progress_service import ProgressService
from src.services.cache_service import CacheService
from src.commands.trading import TradingCommands
from src.config.settings import Settings
from src.config.trading_config import TradingConfig
from src.utils.logger import setup_logger
from src.utils.embeds import create_error_embed, create_info_embed
from src.utils.init_db import initialize_database

# Setup
load_dotenv()
settings = Settings()
logger = setup_logger(__name__)

class CryptoTradingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True

        super().__init__(
            command_prefix=settings.COMMAND_PREFIX,
            intents=intents,
            help_command=None
        )


        self.settings = settings
        self.progress_service = ProgressService()
        self.cache_service: Optional[CacheService] = None

        # Services will be initialized in setup_hook after cache is ready
        self.binance_service = None
        self.dexscreener_service = None
        self.polymarket_service = None
        self.gemini_processor = None
        self.signal_engine = None
        
        # Rate limiting
        self.user_last_request = {}

    async def setup_hook(self):
        """Initialize bot and sync commands"""
        logger.info("Setting up bot...")
        
        # Initialize cache service
        self.cache_service = await initialize_database(self.settings)
        
        # Initialize services with cache
        self.binance_service = BinanceService(self.cache_service)
        self.dexscreener_service = DexScreenerService()
        self.polymarket_service = PolymarketService(self.cache_service)
        self.gemini_processor = GeminiProcessor(self.cache_service)
        self.signal_engine = SignalEngine()

        # Setup commands

        await self.add_cog(TradingCommands(self)) # Add as Cog

        # Sync slash commands
        try:
            if self.settings.GUILD_ID:
                guild = discord.Object(id=self.settings.GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} command(s) to guild {self.settings.GUILD_ID}")
            else:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} command(s) globally")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            
        # Start background tasks
        self.scheduled_analysis.start()
        if self.cache_service:
            self.cache_cleanup.start()

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"✅ Bot is online as {self.user}")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")

        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="📈 Crypto Markets"
        )
        await self.change_presence(activity=activity)

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandOnCooldown):
            embed = create_error_embed(
                "⏱️ Slow down!",
                f"Please wait {error.retry_after:.1f}s before using this command again."
            )
            await ctx.send(embed=embed, ephemeral=True)

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = create_error_embed(
                "❌ Missing Argument",
                f"Missing required argument: `{error.param.name}`"
            )
            await ctx.send(embed=embed, ephemeral=True)

        elif isinstance(error, Exception):
            logger.error(f"Unexpected error: {error}", exc_info=True)
            embed = create_error_embed(
                "💥 Unexpected Error",
                "An unexpected error occurred. Please try again later."
            )
            await ctx.send(embed=embed, ephemeral=True)

    def check_rate_limit(self, user_id: int, cooldown: int = 60) -> bool:
        """Check if user is rate limited"""
        import time
        now = time.time()
        last_request = self.user_last_request.get(user_id, 0)

        if now - last_request < cooldown:
            return False

        self.user_last_request[user_id] = now
        return True

    @tasks.loop(minutes=TradingConfig.ANALYSIS_INTERVAL_MINUTES)
    async def scheduled_analysis(self):
        """Run scheduled market analysis"""
        logger.info("Running scheduled analysis...")
        try:
            # 1. Fetch Polymarket Data & Analyze with Gemini
            events = await self.polymarket_service.get_events()
            gemini_analysis = await self.gemini_processor.analyze_polymarket_events(events)
            
            # 2. Analyze each symbol
            for symbol in TradingConfig.SYMBOLS:
                try:
                    # Fetch MTFA Data
                    async with self.binance_service as bs:
                        mtfa_data = await bs.fetch_mtfa_data(symbol)
                    
                    # Generate Signal
                    signal = self.signal_engine.analyze_market(symbol, mtfa_data, gemini_analysis)
                    
                    if signal.type != "NEUTRAL":
                        logger.info(f"SIGNAL GENERATED: {signal}")
                        
                        # Broadcast to Discord channel if configured
                        if self.settings.SIGNAL_CHANNEL_ID:
                            try:
                                channel = self.get_channel(int(self.settings.SIGNAL_CHANNEL_ID))
                                if channel:
                                    # Create embed
                                    color = discord.Color.green() if signal.type == "BUY" else discord.Color.red()
                                    embed = discord.Embed(
                                        title=f"🚨 {signal.type} Signal: {symbol.replace('/USDT', '')}",
                                        description=f"**Confidence:** {signal.confidence}",
                                        color=color,
                                        timestamp=discord.utils.utcnow()
                                    )
                                    
                                    if signal.entry_price > 0:
                                        embed.add_field(name="💰 Entry", value=f"${signal.entry_price:,.2f}", inline=True)
                                        embed.add_field(name="🛑 SL", value=f"${signal.stop_loss:,.2f}", inline=True)
                                        embed.add_field(name="🎯 TP", value=f"${signal.take_profit:,.2f}", inline=True)
                                        embed.add_field(name="📊 R:R", value=f"{signal.risk_reward_ratio:.2f}", inline=True)
                                    
                                    if signal.reasons:
                                        embed.add_field(
                                            name="💡 Reasons",
                                            value="\n".join([f"• {r}" for r in signal.reasons[:3]]),
                                            inline=False
                                        )
                                    
                                    embed.set_footer(text="Automated Signal • QuantTrade Bot")
                                    await channel.send(embed=embed)
                                    logger.info(f"Signal sent to channel {self.settings.SIGNAL_CHANNEL_ID}")
                            except Exception as e:
                                logger.error(f"Error sending signal to channel: {e}")
                        
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in scheduled analysis: {e}")

    @scheduled_analysis.before_loop
    async def before_scheduled_analysis(self):
        await self.wait_until_ready()
    
    @tasks.loop(hours=1)
    async def cache_cleanup(self):
        """Clean up expired cache entries every hour"""
        if self.cache_service:
            try:
                await self.cache_service.cleanup_expired()
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    @cache_cleanup.before_loop
    async def before_cache_cleanup(self):
        await self.wait_until_ready()

async def main():
    """Main entry point"""
    bot = CryptoTradingBot()

    try:
        async with bot:
            await bot.start(settings.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        await bot.close()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)

if __name__ == "__main__":
    # Run bot
    asyncio.run(main())