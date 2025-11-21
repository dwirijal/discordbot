import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging
from ..config.trading_config import TradingConfig
from ..utils.embeds import create_info_embed, create_error_embed

logger = logging.getLogger(__name__)

class TradingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="Show current market status overview")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Fetch Gemini Analysis
            events = await self.bot.polymarket_service.get_events()
            gemini_analysis = await self.bot.gemini_processor.analyze_polymarket_events(events)
            
            embed = discord.Embed(
                title="🌍 Market Status Overview",
                color=discord.Color.blue()
            )
            
            # Add Gemini Sentiment
            sentiment = gemini_analysis.get('sentiment', 'UNKNOWN')
            score = gemini_analysis.get('score', 0)
            summary = gemini_analysis.get('summary', 'No data')
            
            embed.add_field(
                name="🤖 Gemini Sentiment Analysis",
                value=f"**Sentiment:** {sentiment}\n**Score:** {score}/10\n**Summary:** {summary}",
                inline=False
            )
            
            # Add list of tracked symbols
            symbols = ", ".join(TradingConfig.SYMBOLS)
            embed.add_field(name="Tracked Symbols", value=symbols, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await interaction.followup.send(embed=create_error_embed("Error", str(e)))

    @app_commands.command(name="coin", description="Analyze cryptocurrency with optional timeframe and sentiment")
    @app_commands.describe(
        symbol="Coin symbol (e.g., BTC, ETH, SOL)",
        timeframe="Optional timeframe (e.g., 15m, 1h, 4h, 1d)",
        sentiment="Include sentiment analysis (yes/no)"
    )
    async def coin(
        self, 
        interaction: discord.Interaction, 
        symbol: str,
        timeframe: Optional[str] = None,
        sentiment: Optional[str] = None
    ):
        await interaction.response.defer()
        try:
            # Normalize symbol (remove /USDT if present, convert to uppercase)
            symbol = symbol.upper().replace("/USDT", "").replace("USDT", "").strip()
            
            # Add /USDT suffix for internal processing
            trading_pair = f"{symbol}/USDT"
            
            # Determine if sentiment analysis is requested
            include_sentiment = sentiment and sentiment.lower() in ['yes', 'y', 'true', '1', 'sentiment']
            
            # Use default timeframe if not provided
            selected_timeframe = timeframe if timeframe else "15m"
            
            # Fetch MTFA Data
            async with self.bot.binance_service as bs:
                mtfa_data = await bs.fetch_mtfa_data(trading_pair)
                
            # Fetch Sentiment if requested
            gemini_analysis = {}
            if include_sentiment:
                events = await self.bot.polymarket_service.get_events()
                gemini_analysis = await self.bot.gemini_processor.analyze_polymarket_events(events)
            
            # Analyze
            signal = self.bot.signal_engine.analyze_market(trading_pair, mtfa_data, gemini_analysis)
            
            # Create Embed
            color = discord.Color.greyple()
            if signal.type == "BUY": color = discord.Color.green()
            elif signal.type == "SELL": color = discord.Color.red()
            
            embed = discord.Embed(
                title=f"📊 {symbol} Analysis",
                description=f"**Signal:** {signal.type}\n**Confidence:** {signal.confidence}\n**Timeframe:** {selected_timeframe}",
                color=color,
                timestamp=discord.utils.utcnow()
            )
            
            # Price Information
            if signal.entry_price > 0:
                embed.add_field(name="💰 Entry", value=f"${signal.entry_price:,.2f}", inline=True)
                embed.add_field(name="🛑 Stop Loss", value=f"${signal.stop_loss:,.2f}", inline=True)
                embed.add_field(name="🎯 Take Profit", value=f"${signal.take_profit:,.2f}", inline=True)
                embed.add_field(name="📊 R:R Ratio", value=f"{signal.risk_reward_ratio:.2f}", inline=True)
            
            # MTFA Summary
            if signal.mtfa_analysis:
                mtfa_text = ""
                for tf, status in signal.mtfa_analysis.items():
                    icon = "🟢" if status == "BULLISH" else "🔴" if status == "BEARISH" else "⚪"
                    mtfa_text += f"**{tf}:** {icon} {status}\n"
                embed.add_field(name="📈 Multi-Timeframe Analysis", value=mtfa_text, inline=False)
            
            # Reasons
            if signal.reasons:
                reasons_text = "\n".join([f"• {r}" for r in signal.reasons[:5]])
                embed.add_field(name="💡 Analysis Reasons", value=reasons_text, inline=False)
            
            # Sentiment (if requested)
            if include_sentiment and gemini_analysis:
                sentiment_text = f"**Sentiment:** {gemini_analysis.get('sentiment', 'N/A')}\n"
                sentiment_text += f"**Score:** {gemini_analysis.get('score', 0)}/10\n"
                sentiment_text += f"**Summary:** {gemini_analysis.get('summary', 'No data')[:100]}..."
                embed.add_field(name="🤖 Market Sentiment", value=sentiment_text, inline=False)
            
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in coin command: {e}")
            await interaction.followup.send(embed=create_error_embed("Error", str(e)))

