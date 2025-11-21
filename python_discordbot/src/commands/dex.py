import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time
from typing import Optional

from ..services.dexscreener_service import DexScreenerService
from ..services.progress_service import ProgressService
from ..utils.embeds import create_dex_embed
from ..models.dex_data import DexAnalysisData

class DexCommand(commands.Command):
    def __init__(self, bot):
        self.bot = bot
        self.dex_service = DexScreenerService()
        self.progress_service = ProgressService()

        # Create command
        command = app_commands.Command(
            name="dex",
            description="Analyze DEX token data from DexScreener",
            callback=self.execute,
            options=[
                app_commands.Option(
                    name="query",
                    description="Token symbol or contract address",
                    type=app_commands.OptionType.string,
                    required=True
                )
            ]
        )

        self.name = "dex"
        self.callback = command.callback
        bot.tree.add_command(command)

    async def execute(self, interaction: discord.Interaction, query: str):
        """Handle /dex command"""
        # Check rate limit
        if not self.bot.check_rate_limit(interaction.user.id, 30):
            await interaction.response.send_message(
                "⏱️ Please wait 30 seconds before using this command again.",
                ephemeral=True
            )
            return

        # Defer response
        await interaction.response.defer()

        # Initialize progress tracking
        progress = await self.progress_service.create_progress(
            interaction,
            title="🔍 DEX Analysis",
            max_steps=4
        )

        try:
            # Step 1: Parse query
            await progress.update(
                step=1,
                message="🔍 Parsing query..."
            )

            is_address = self.dex_service.is_contract_address(query)
            search_query = query.upper() if not is_address else query

            # Step 2: Fetch data
            await progress.update(
                step=2,
                message="📊 Fetching data from DexScreener..."
            )

            data = await self.dex_service.get_token_data(
                address=search_query if is_address else None,
                symbol=search_query if not is_address else None
            )

            if not data or not data.get('pairs'):
                await progress.finalize(
                    message=f"❌ Token not found: `{query}`",
                    error=True
                )
                return

            # Step 3: Analyze data
            await progress.update(
                step=3,
                message="🧠 Analyzing token metrics..."
            )

            analysis = await self.analyze_token(data)

            # Step 4: Create embed
            await progress.update(
                step=4,
                message="📨 Creating response..."
            )

            embed = create_dex_embed(analysis)

            # Final response
            await progress.finalize(embed=embed)

        except Exception as e:
            await self.progress_service.handle_error(progress, e, query)

    async def analyze_token(self, data: dict) -> DexAnalysisData:
        """Analyze token data and generate insights"""
        pairs = data.get('pairs', [])

        # Filter liquid pairs
        liquid_pairs = [p for p in pairs if p.get('liquidity', {}).get('usd', 0) > 100]

        if not liquid_pairs:
            raise ValueError("No liquid pairs found")

        # Sort by liquidity
        best_pair = max(liquid_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))

        # Extract base and quote token info
        base_token = best_pair.get('baseToken', {})
        quote_token = best_pair.get('quoteToken', {})

        # Price data
        price_usd = float(best_pair.get('priceUsd', 0))
        price_native = float(best_pair.get('priceNative', 0))

        # Liquidity data
        liquidity = best_pair.get('liquidity', {})
        liq_usd = float(liquidity.get('usd', 0))
        liq_base = float(liquidity.get('base', 0))
        liq_quote = float(liquidity.get('quote', 0))

        # Volume data
        volume = best_pair.get('volume', {})
        vol_24h = float(volume.get('h24', 0))

        # Transaction data
        txns = best_pair.get('txns', {})
        buys_24h = txns.get('h24', {}).get('buys', 0)
        sells_24h = txns.get('h24', {}).get('sells', 0)
        total_txns = buys_24h + sells_24h
        buy_ratio = (buys_24h / total_txns * 100) if total_txns > 0 else 50

        # Market cap
        mcap = float(best_pair.get('marketCap', 0))
        fdv = float(best_pair.get('fdv', 0))

        # Price changes
        price_change = best_pair.get('priceChange', {})
        changes = {
            'm5': float(price_change.get('m5', 0)),
            'h1': float(price_change.get('h1', 0)),
            'h6': float(price_change.get('h6', 0)),
            'h24': float(price_change.get('h24', 0))
        }

        # Socials and boosts
        info = best_pair.get('info', {})
        socials = info.get('socials', [])
        boosts = best_pair.get('boosts', {}).get('active', 0)

        # Age calculation
        created_at = best_pair.get('pairCreatedAt', 0)
        age_hours = (time.time() * 1000 - created_at) / (1000 * 60 * 60)

        # Risk assessment
        risk_flags = []
        if liq_usd < 1000:
            risk_flags.append("💀 Low Liquidity")
        if len(socials) == 0:
            risk_flags.append("⚠️ No Socials")
        if buy_ratio < 30:
            risk_flags.append("🔴 Low Buy Pressure")

        # Signal generation
        score = 0
        signal = "NEUTRAL"

        if liq_usd > 10000:
            score += 2
        if buy_ratio > 60:
            score += 2
        if changes['h24'] > 10:
            score += 1
        if len(socials) > 2:
            score += 1

        if score >= 4:
            signal = "BUY 🚀"
        elif score <= -2:
            signal = "AVOID ☠️"
        elif score >= 2:
            signal = "ACCUMULATE 🟢"

        # Explorer URL
        chain_id = best_pair.get('chainId', '').lower()
        address = base_token.get('address', '')
        explorer_url = self.get_explorer_url(chain_id, address)

        return DexAnalysisData(
            name=base_token.get('name', 'Unknown'),
            symbol=base_token.get('symbol', 'UNK'),
            address=address,
            price_usd=price_usd,
            price_native=price_native,
            quote_symbol=quote_token.get('symbol', 'QUOTE'),
            dex_id=best_pair.get('dexId', 'Unknown'),
            chain=best_pair.get('chainId', 'Unknown'),
            url=best_pair.get('url', ''),
            image_url=info.get('imageUrl', ''),
            explorer_url=explorer_url,

            signal=signal,
            age_hours=age_hours,
            social_count=len(socials),
            boosts=boosts,

            market_cap=mcap,
            liquidity_usd=liq_usd,
            volume_24h=vol_24h,
            turnover_ratio=(vol_24h / mcap * 100) if mcap > 0 else 0,

            buy_ratio=buy_ratio,
            buys_count=buys_24h,
            sells_count=sells_24h,

            changes=changes,

            liq_base=liq_base,
            liq_quote=liq_quote,

            risk_flags=' | '.join(risk_flags) if risk_flags else "None",

            color=self.get_signal_color(signal)
        )

    def get_explorer_url(self, chain_id: str, address: str) -> str:
        """Get explorer URL based on chain"""
        explorers = {
            'ethereum': f'https://etherscan.io/token/{address}',
            'bsc': f'https://bscscan.com/token/{address}',
            'polygon': f'https://polygonscan.com/token/{address}',
            'arbitrum': f'https://arbiscan.io/token/{address}',
            'avalanche': f'https://snowtrace.io/token/{address}',
            'fantom': f'https://ftmscan.com/token/{address}',
            'solana': f'https://solscan.io/token/{address}',
            'base': f'https://basescan.org/token/{address}'
        }
        return explorers.get(chain_id, f'https://etherscan.io/token/{address}')

    def get_signal_color(self, signal: str) -> int:
        """Get Discord embed color based on signal"""
        colors = {
            'BUY 🚀': 0x00ff00,
            'ACCUMULATE 🟢': 0x90ee90,
            'NEUTRAL': 0xffff00,
            'AVOID ☠️': 0xff0000
        }
        return colors.get(signal, 0x808080)