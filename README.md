# 🚀 Discord Crypto Analyzer Bot

A powerful Discord bot that provides real-time cryptocurrency technical analysis across multiple timeframes, with sentiment analysis from Polymarket and AI-powered insights.

## ✨ Features

### 📊 Technical Analysis
- **6 Timeframes**: 15m, 1h, 4h, 1d, 1w, 1M
- **Indicators**: RSI, MACD, Moving Averages, Bollinger Bands
- **Key Levels**: Automatic support & resistance identification
- **Risk Metrics**: Volatility assessment and suggested SL/TP

### 🎯 Smart Features
- **Progressive Updates**: Real-time progress bars during analysis
- **Sentiment Analysis**: Polymarket prediction market integration
- **AI Insights**: Claude AI-powered market analysis
- **Smart Caching**: Optimized response times with intelligent caching

### 🛡️ Safety Features
- **Rate Limiting**: Built-in protection against API limits
- **Error Handling**: Graceful error recovery and user feedback
- **Data Validation**: Input validation and sanitization

## 🚀 Quick Start

### Prerequisites
- Node.js 16.11.0 or higher
- Discord Bot Token
- API keys (optional for enhanced features)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd discordbot
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Deploy Discord commands**
```bash
npm run deploy
```

5. **Start the bot**
```bash
npm start
# For development with auto-reload:
npm run dev
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following:

```env
# Discord Configuration (Required)
DISCORD_TOKEN=your_discord_bot_token_here
CLIENT_ID=your_discord_application_client_id
GUILD_ID=your_discord_server_id

# API Keys (Optional - enables enhanced features)
BINANCE_API_KEY=your_binance_api_key
POLYMARKET_API_KEY=your_polymarket_api_key
CLAUDE_API_KEY=your_claude_api_key

# Rate Limiting
RATE_LIMIT_WINDOW=60000
RATE_LIMIT_MAX_REQUESTS=10

# Cache Settings
CACHE_TTL=60000
ANALYSIS_COOLDOWN=120000

# Feature Flags
ENABLE_AI_ANALYSIS=true
ENABLE_POLYMARKET=true
ENABLE_CACHING=true
```

### Discord Bot Setup

1. **Create Discord Application**
   - Go to https://discord.com/developers/applications
   - Create a "New Application"
   - Go to "Bot" tab and create a bot

2. **Enable Privileged Intents**
   - Message Content Intent
   - Server Members Intent (if needed)

3. **Invite Bot to Server**
   - Generate OAuth2 URL with `bot` and `applications.commands` scopes
   - Invite bot to your server with Administrator permissions

## 📋 Commands

### `/analyze [symbol]`
Analyze a cryptocurrency for technical indicators and signals.

**Arguments:**
- `symbol` (required): Cryptocurrency symbol (e.g., BTC, ETH, SOL)
- `timeframe` (optional): Specific timeframe to analyze

**Examples:**
```
/analyze BTC
/analyze ETH timeframe:1h
/analyze SOL timeframe:4h
```

### Response Format

The bot provides a comprehensive analysis including:
- Current price and 24h change
- Technical indicators (RSI, MACD, MAs)
- Support & resistance levels
- Trading signals with confidence scores
- Sentiment analysis from prediction markets
- AI-powered recommendations

## 🔧 Advanced Configuration

### Custom Timeframes

Modify the timeframes in `src/services/cryptoService.js`:
```javascript
const timeframes = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'];
```

### Adding New Indicators

Add new technical indicators in the `calculateTechnicalIndicators` method:
```javascript
const newIndicator = CustomIndicator.calculate({
  values: closes,
  period: 14
});
```

### Customizing Progress Messages

Modify the progress steps in `src/handlers/analyze.js`:
```javascript
await progress.update(1, 8, '📊 Custom step message...');
```

## 📊 Supported Exchanges

- **Binance**: Primary data source for price and volume
- **Polymarket**: Sentiment analysis from prediction markets
- **CoinMarketCap**: Additional market data (planned)

## 🛠️ Development

### Project Structure
```
discordbot/
├── src/
│   ├── handlers/        # Discord command handlers
│   ├── services/        # External API integrations
│   ├── utils/           # Utility functions
│   ├── config/          # Configuration files
│   └── index.js         # Bot entry point
├── data/                # Data storage
├── logs/                # Log files
└── package.json
```

### Adding New Commands

1. Create a new file in `src/handlers/`
2. Export a command object with `data` and `execute` properties
3. The bot will automatically load it

### Testing

```bash
npm test
```

### Linting

```bash
npm run lint
```

## 🔒 Security

- Input validation on all user inputs
- Rate limiting to prevent abuse
- Secure storage of API keys
- Error handling prevents information leakage

## 📈 Performance

- **Response Time**: 8-12 seconds for full analysis
- **Cache**: 60-second TTL for repeated requests
- **Rate Limits**: 10 requests per minute per user
- **Memory Usage**: <100MB idle

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 Changelog

### v1.0.0
- Initial release
- Multi-timeframe analysis
- Polymarket integration
- Progressive loading
- Technical indicators

## ❓ FAQ

**Q: How long does analysis take?**
A: Typically 8-12 seconds depending on API response times.

**Q: Can I add custom cryptocurrencies?**
A: Yes, any symbol with USDT pair on Binance is supported.

**Q: Is the financial advice?**
A: No! Always do your own research before making trades.

**Q: Can I run multiple instances?**
A: Yes, but ensure they don't share the same Discord token.

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Discord.js for the Discord API wrapper
- Technical Indicators library for calculations
- Binance API for market data
- Polymarket for sentiment data

## 📞 Support

For issues and support:
1. Check the [Issues](https://github.com/your-repo/issues) page
2. Create a new issue with details
3. Join our Discord server for live support

---

⚠️ **Disclaimer**: This bot is for informational purposes only. Not financial advice. Cryptocurrency trading involves risk.