import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import numpy as np
from typing import Optional

from ..services.binance_service import BinanceService
from ..services.progress_service import ProgressService
from ..utils.embeds import create_analysis_embed
from ..services.indicators import TechnicalIndicators, AdvancedAnalytics

class AnalyzeCommand(commands.Command):
    def __init__(self, bot):
        self.bot = bot
        self.progress_service = ProgressService()

        # Create command
        command = app_commands.Command(
            name="analyze",
            description="Analyze cryptocurrency technical analysis",
            callback=self.execute,
            options=[
                app_commands.Option(
                    name="symbol",
                    description="Cryptocurrency symbol (e.g., BTC, ETH)",
                    type=app_commands.OptionType.string,
                    required=True
                ),
                app_commands.Option(
                    name="timeframe",
                    description="Timeframe for analysis",
                    type=app_commands.OptionType.string,
                    choices=[
                        app_commands.Choice(name="1 minute", value="1m"),
                        app_commands.Choice(name="5 minutes", value="5m"),
                        app_commands.Choice(name="15 minutes", value="15m"),
                        app_commands.Choice(name="30 minutes", value="30m"),
                        app_commands.Choice(name="1 hour", value="1h"),
                        app_commands.Choice(name="4 hours", value="4h"),
                        app_commands.Choice(name="1 day", value="1d"),
                        app_commands.Choice(name="1 week", value="1w")
                    ],
                    required=False
                )
            ]
        )

        self.name = "analyze"
        self.callback = command.callback
        bot.tree.add_command(command)

    async def execute(self, interaction: discord.Interaction,
                     symbol: str, timeframe: str = "15m"):
        """Handle /analyze command"""
        # Check rate limit
        if not self.bot.check_rate_limit(interaction.user.id, 30):
            await interaction.response.send_message(
                "⏱️ Please wait 30 seconds before using this command again.",
                ephemeral=True
            )
            return

        # Sanitize input
        symbol = symbol.upper().replace("-", "").strip()
        if not symbol or len(symbol) > 20:
            await interaction.response.send_message(
                "❌ Invalid symbol. Please use a valid cryptocurrency symbol.",
                ephemeral=True
            )
            return

        # Initialize progress
        progress = await self.progress_service.create_progress(
            interaction,
            title=f"📊 Analyzing {symbol}",
            max_steps=8
        )

        try:
            # Step 1: Initialize service
            await progress.update(1, "🔧 Initializing analysis service...")
            async with BinanceService() as binance:
                pass  # Test connection

            # Step 2: Fetch kline data
            await progress.update(2, f"📈 Fetching {timeframe} data...")
            async with BinanceService() as binance:
                df = await binance.get_klines(f"{symbol}USDT", timeframe, limit=200)

            if df.empty:
                await progress.finalize(
                    message=f"❌ No data found for {symbol}. Please check the symbol.",
                    error=True
                )
                return

            # Step 3: Calculate basic indicators
            await progress.update(3, "📊 Calculating technical indicators...")
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            volumes = df['volume'].values

            # Calculate all indicators
            indicators = {}

            # Moving averages
            indicators['sma_20'] = TechnicalIndicators.sma(closes, 20)[-1]
            indicators['sma_50'] = TechnicalIndicators.sma(closes, 50)[-1]
            indicators['sma_200'] = TechnicalIndicators.sma(closes, 200)[-1]
            indicators['ema_20'] = TechnicalIndicators.ema(closes, 20)[-1]

            # RSI and StochRSI
            indicators['rsi'] = TechnicalIndicators.rsi(closes, 14)[-1]
            slowk, slowd = TechnicalIndicators.stochastic_oscillator(highs, lows, closes)
            indicators['stoch_k'] = slowk[-1]
            indicators['stoch_d'] = slowd[-1]

            # MACD
            macd, signal_line, histogram = TechnicalIndicators.macd(closes)
            indicators['macd'] = macd[-1]
            indicators['macd_signal'] = signal_line[-1]
            indicators['macd_histogram'] = histogram[-1]

            # Bollinger Bands
            upper, middle, lower = TechnicalIndicators.bollinger_bands(closes)
            indicators['bb_upper'] = upper[-1]
            indicators['bb_middle'] = middle[-1]
            indicators['bb_lower'] = lower[-1]

            # Step 4: Advanced indicators
            await progress.update(4, "🧠 Computing advanced metrics...")

            # ATR and volatility
            atr = TechnicalIndicators.atr(highs, lows, closes)
            indicators['atr'] = atr[-1]
            indicators['volatility'] = (atr[-1] / closes[-1]) * 100

            # VWAP
            vwap = TechnicalIndicators.vwap(highs, lows, closes, volumes)
            indicators['vwap'] = vwap[-1]

            # CMF (Money Flow)
            cmf = TechnicalIndicators.cmf(highs, lows, closes, volumes)
            indicators['cmf'] = cmf[-1] if not np.isnan(cmf[-1]) else 0

            # Williams %R
            wr = TechnicalIndicators.williams_r(highs, lows, closes)
            indicators['williams_r'] = wr[-1] if not np.isnan(wr[-1]) else -50

            # ADX
            adx = TechnicalIndicators.adx(highs, lows, closes)
            indicators['adx'] = adx[-1] if not np.isnan(adx[-1]) else 0

            # Step 5: Structure analysis
            await progress.update(5, "🏗️ Analyzing market structure...")

            # Find fractals
            fractal_highs, fractal_lows = AdvancedAnalytics.detect_fractals(closes)
            recent_highs = [fh for fh in fractal_highs if fh > 0][-5:]
            recent_lows = [fl for fl in fractal_lows if fl > 0][-5:]

            # Find key levels
            resistance = max(recent_highs) if recent_highs else closes[-1] * 1.1
            support = min(recent_lows) if recent_lows else closes[-1] * 0.9

            # Fibonacci levels
            fib_levels = TechnicalIndicators.fibonacci_retracements(
                max(highs[-100:]),
                min(lows[-100:])
            )

            # Pivot points
            pivot_points = TechnicalIndicators.pivot_points(
                highs[-1],
                lows[-1],
                closes[-1]
            )

            # Step 6: Divergence detection
            await progress.update(6, "🔍 Detecting divergences...")

            # Check for RSI divergences
            rsi_values = TechnicalIndicators.rsi(closes)
            divergences = AdvancedAnalytics.detect_divergence(closes, rsi_values)

            # Step 7: Signal generation
            await progress.update(7, "🎯 Generating trading signals...")

            # Calculate signal score
            signal_score = 0
            signals = []

            # RSI signal
            rsi = indicators['rsi']
            if rsi < 30:
                signals.append("RSI Oversold")
                signal_score += 2
            elif rsi > 70:
                signals.append("RSI Overbought")
                signal_score -= 2

            # MACD signal
            if indicators['macd_histogram'] > 0:
                signals.append("MACD Bullish")
                signal_score += 2
            else:
                signals.append("MACD Bearish")
                signal_score -= 2

            # MA trend
            if closes[-1] > indicators['sma_20'] > indicators['sma_50']:
                signals.append("Uptrend")
                signal_score += 2
            elif closes[-1] < indicators['sma_20'] < indicators['sma_50']:
                signals.append("Downtrend")
                signal_score -= 2

            # Volume analysis
            avg_volume = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            if current_volume > avg_volume * 1.5:
                signals.append("High Volume")
                signal_score += 1

            # Determine final signal
            if signal_score >= 4:
                final_signal = "STRONG BUY"
                color = discord.Color.green()
            elif signal_score >= 2:
                final_signal = "BUY"
                color = discord.Color.dark_green()
            elif signal_score >= -1:
                final_signal = "HOLD"
                color = discord.Color.yellow()
            elif signal_score >= -3:
                final_signal = "SELL"
                color = discord.Color.red()
            else:
                final_signal = "STRONG SELL"
                color = discord.Color.dark_red()

            # Step 8: Get ticker data
            await progress.update(8, "📋 Fetching market data...")

            async with BinanceService() as binance:
                ticker = await binance.get_ticker_24hr(f"{symbol}USDT")

            # Compile analysis data
            analysis_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': closes[-1],
                'price_change_24h': float(ticker.get('priceChangePercent', 0)),
                'volume_24h': float(ticker.get('volume', 0)),
                'high_24h': float(ticker.get('highPrice', 0)),
                'low_24h': float(ticker.get('lowPrice', 0)),

                'indicators': indicators,
                'levels': {
                    'resistance': resistance,
                    'support': support,
                    'fibonacci': fib_levels,
                    'pivots': pivot_points
                },
                'signal': {
                    'action': final_signal,
                    'score': signal_score,
                    'reasons': signals[:5],
                    'color': color
                },
                'divergences': divergences,
                'timestamp': discord.utils.utcnow()
            }

            # Create final embed
            embed = create_analysis_embed(analysis_data)

            # Send final result
            await progress.finalize(embed=embed)

        except Exception as e:
            await self.progress_service.handle_error(progress, e, f"Analyzing {symbol}")