module.exports = {
  // Bot Configuration
  bot: {
    token: process.env.DISCORD_TOKEN,
    clientId: process.env.CLIENT_ID,
    guildId: process.env.GUILD_ID,
    prefix: '!'
  },

  // API Configuration
  apis: {
    binance: {
      baseUrl: 'https://api.binance.com',
      timeout: 10000,
      retries: 3
    },
    polymarket: {
      baseUrl: 'https://gamma-api.polymarket.com',
      timeout: 10000,
      retries: 2
    },
    claude: {
      baseUrl: 'https://api.anthropic.com/v1',
      timeout: 15000,
      retries: 2
    }
  },

  // Rate Limiting
  rateLimiting: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW) || 60000, // 1 minute
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 10,
    cooldown: parseInt(process.env.ANALYSIS_COOLDOWN) || 120000 // 2 minutes
  },

  // Caching
  cache: {
    ttl: parseInt(process.env.CACHE_TTL) || 60000, // 1 minute
    maxSize: 1000,
    checkPeriod: 600000 // 10 minutes
  },

  // Technical Analysis Settings
  analysis: {
    timeframes: ['15m', '1h', '4h', '1d', '1w', '1M'],
    indicators: {
      rsi: {
        period: 14,
        overbought: 70,
        oversold: 30
      },
      macd: {
        fast: 12,
        slow: 26,
        signal: 9
      },
      bollingerBands: {
        period: 20,
        stdDev: 2
      }
    }
  },

  // Feature Flags
  features: {
    aiAnalysis: process.env.ENABLE_AI_ANALYSIS === 'true',
    polymarket: process.env.ENABLE_POLYMARKET === 'true',
    caching: process.env.ENABLE_CACHING !== 'false',
    logging: process.env.ENABLE_LOGGING !== 'false'
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: {
      enabled: true,
      filename: 'logs/bot.log',
      maxSize: '5m',
      maxFiles: '7d'
    },
    console: {
      enabled: true,
      colorize: true
    }
  },

  // Progress Updates
  progress: {
    minUpdateInterval: 2000, // Minimum 2 seconds between updates
    maxSteps: 10,
    timeout: 60000 // 1 minute max analysis time
  },

  // Security
  security: {
    maxSymbolLength: 10,
    allowedSymbols: /^[A-Z0-9]+$/,
    sanitizeInput: true,
    maxRequestsPerUser: 50
  },

  // Error Handling
  errors: {
    retryAttempts: 3,
    retryDelay: 1000,
    notifyOnError: true
  }
};