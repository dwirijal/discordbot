import discord
from typing import Dict, Any, Optional

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized error embed"""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red()
    )
    embed.set_footer(text="Please try again or contact support if the issue persists")
    return embed

def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized info embed"""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=discord.Color.blue()
    )
    return embed

def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized success embed"""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green()
    )
    return embed

def create_analysis_embed(data: Dict[str, Any]) -> discord.Embed:
    """Create a comprehensive analysis embed"""
    embed = discord.Embed(
        title=f"📊 {data['symbol']}/USDT Analysis - {data['timeframe'].upper()}",
        color=data['signal']['color']
    )

    # Current price section
    price_change_color = "🟢" if data['price_change_24h'] >= 0 else "🔴"
    embed.description = f"**Current Price:** ${data['current_price']:.6f} {price_change_color} ({data['price_change_24h']:+.2f}%)"

    # Signal section
    embed.add_field(
        name=f"🎯 SIGNAL: {data['signal']['action']}",
        value=f"Confidence: {abs(data['signal']['score']) * 20:.0f}%\n" +
              f"Reasons: {', '.join(data['signal']['reasons'])}",
        inline=False
    )

    # Technical Indicators
    indicators = data['indicators']
    embed.add_field(
        name="📈 Technical Indicators",
        value=f"**RSI(14):** {indicators['rsi']:.1f} {get_rsi_emoji(indicators['rsi'])}\n" +
              f"**MACD:** {get_macd_signal(indicators['macd_histogram'])}\n" +
              f"**Volume:** {format_volume(data['volume_24h'])}",
        inline=True
    )

    # Moving Averages
    embed.add_field(
        name="📊 Moving Averages",
        value=f"**SMA 20:** ${indicators['sma_20']:.6f}\n" +
              f"**SMA 50:** ${indicators['sma_50']:.6f}\n" +
              f"**VWAP:** ${indicators['vwap']:.6f}",
        inline=True
    )

    # Key Levels
    levels = data['levels']
    embed.add_field(
        name="🏗️ Key Levels",
        value=f"**Resistance:** ${levels['resistance']:.6f}\n" +
              f"**Support:** ${levels['support']:.6f}\n" +
              f"**ATR:** {indicators['atr']:.6f} ({indicators['volatility']:.1f}%)",
        inline=True
    )

    # Market Structure
    structure_status = get_market_structure_status(
        data['current_price'],
        indicators['sma_20'],
        indicators['sma_50'],
        indicators['vwap']
    )
    embed.add_field(
        name="🏛️ Market Structure",
        value=structure_status,
        inline=False
    )

    # Divergences
    if data['divergences']['bullish'] or data['divergences']['bearish']:
        div_text = ""
        if data['divergences']['bullish']:
            div_text += f"🟢 Bullish Divergence: {len(data['divergences']['bullish'])} detected\n"
        if data['divergences']['bearish']:
            div_text += f"🔴 Bearish Divergence: {len(data['divergences']['bearish'])} detected"

        embed.add_field(
            name="🔍 Divergences",
            value=div_text,
            inline=False
        )

    # Fibonacci Levels (key levels only)
    fib = levels['fibonacci']
    embed.add_field(
        name="📐 Fibonacci Levels",
        value=f"**38.2%:** ${fib['38.2%']:.6f}\n" +
              f"**61.8%:** ${fib['61.8%']:.6f}\n" +
              f"**78.6%:** ${fib['78.6%']:.6f}",
        inline=True
    )

    # Pivot Points
    pivots = levels['pivots']
    embed.add_field(
        name="⚖️ Pivot Points",
        value=f"**R1:** ${pivots['R1']:.6f}\n" +
              f"**PP:** ${pivots['PP']:.6f}\n" +
              f"**S1:** ${pivots['S1']:.6f}",
        inline=True
    )

    # Footer
    embed.set_footer(
        text=f"Analysis based on {data['timeframe']} timeframe • Not financial advice"
    )
    embed.timestamp = data['timestamp']

    return embed

def create_dex_embed(data) -> discord.Embed:
    """Create a DEX analysis embed"""
    token = data['token']
    price = data['price']
    market = data['market']
    transactions = data['transactions']
    metadata = data['metadata']

    embed = discord.Embed(
        title=f"🦄 DEX Analysis: {token['name']} ({token['symbol']})",
        url=metadata['url'],
        color=get_score_color(data['scores']['overall'])
    )

    # Token info
    embed.description = (
        f"**Price:** ${price['usd']:.6f} ({price['changes'].get('h24', 0):+.2f}%)\n" +
        f"**Chain:** {metadata['chain'].upper()} • **DEX:** {metadata['dex'].upper()}\n" +
        f"[Explorer]({metadata['explorer_url']})"
    )

    # Token image if available
    if token['image_url']:
        embed.set_thumbnail(url=token['image_url'])

    # Signal
    embed.add_field(
        name=f"🎯 SIGNAL: {data['signal']}",
        value=data['recommendation'],
        inline=False
    )

    # Market Metrics
    embed.add_field(
        name="💰 Market Metrics",
        value=f"**Market Cap:** ${format_number(market['market_cap'])}\n" +
              f"**Liquidity:** ${format_number(market['liquidity']['usd'])}\n" +
              f"**Volume 24h:** ${format_number(market['volume']['24h'])}\n" +
              f"**Turnover:** {market['turnover_ratio']:.1f}%",
        inline=True
    )

    # Trading Activity
    embed.add_field(
        name="📊 Trading Activity",
        value=f"**Buy Ratio:** {transactions['buy_ratio']:.1f}%\n" +
              f"**Buys:** {transactions['buys_24h']}\n" +
              f"**Sells:** {transactions['sells_24h']}\n" +
              f"**Total Txns:** {transactions['total_24h']}",
        inline=True
    )

    # Scores
    scores = data['scores']
    embed.add_field(
        name="📈 Scores",
        value=f"**Overall:** {scores['overall']}/100\n" +
              f"**Liquidity:** {scores['liquidity']}/100\n" +
              f"**Volume:** {scores['volume']}/100\n" +
              f"**Risk:** {scores['risk']}/100",
        inline=True
    )

    # Risk flags
    if data['scam_flags']:
        embed.add_field(
            name="⚠️ Risk Flags",
            value="\n".join(data['scam_flags'][:3]),
            inline=False
        )

    # Socials
    if metadata['socials']:
        social_text = []
        for social in metadata['socials'][:3]:
            if social.get('type') == 'twitter':
                social_text.append(f"🐦 Twitter")
            elif social.get('type') == 'telegram':
                social_text.append(f"📱 Telegram")
            elif social.get('type') == 'website':
                social_text.append(f"🌐 Website")

        if social_text:
            embed.add_field(
                name="🔗 Social Presence",
                value=" • ".join(social_text),
                inline=True
            )

    # Footer
    embed.set_footer(
        text=f"Age: {metadata['age_hours']:.1f}h • "
             f"Boosts: {metadata['boosts']} • "
             f"Not financial advice"
    )
    embed.timestamp = discord.utils.utcnow()

    return embed

def get_rsi_emoji(rsi: float) -> str:
    """Get emoji for RSI value"""
    if rsi >= 70:
        return "🔴 (Overbought)"
    elif rsi <= 30:
        return "🟢 (Oversold)"
    else:
        return "🟡 (Neutral)"

def get_macd_signal(histogram: float) -> str:
    """Get MACD signal description"""
    if histogram > 0:
        return "🟢 Bullish"
    else:
        return "🔴 Bearish"

def format_volume(volume: float) -> str:
    """Format volume with appropriate units"""
    if volume >= 1e9:
        return f"${volume/1e9:.1f}B"
    elif volume >= 1e6:
        return f"${volume/1e6:.1f}M"
    elif volume >= 1e3:
        return f"${volume/1e3:.1f}K"
    else:
        return f"${volume:.2f}"

def format_number(num: float) -> str:
    """Format large numbers"""
    if num >= 1e9:
        return f"{num/1e9:.1f}B"
    elif num >= 1e6:
        return f"{num/1e6:.1f}M"
    elif num >= 1e3:
        return f"{num/1e3:.1f}K"
    else:
        return f"{num:.2f}"

def get_market_structure_status(price: float, sma20: float,
                               sma50: float, vwap: float) -> str:
    """Determine market structure status"""
    status = []

    if price > sma20 > sma50:
        status.append("🟢 Strong Uptrend")
    elif price < sma20 < sma50:
        status.append("🔴 Strong Downtrend")
    elif price > sma20:
        status.append("🟡 Bullish")
    elif price < sma20:
        status.append("🟡 Bearish")
    else:
        status.append("⚪ Neutral")

    if price > vwap:
        status.append("Above VWAP")
    else:
        status.append("Below VWAP")

    return " • ".join(status)

def get_score_color(score: float) -> discord.Color:
    """Get color based on score"""
    if score >= 75:
        return discord.Color.green()
    elif score >= 60:
        return discord.Color.dark_green()
    elif score >= 40:
        return discord.Color.yellow()
    elif score >= 25:
        return discord.Color.orange()
    else:
        return discord.Color.red()