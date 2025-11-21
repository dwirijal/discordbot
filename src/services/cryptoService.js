const axios = require('axios');
const { RSI, MACD, SMA, EMA, BollingerBands } = require('technicalindicators');

class CryptoService {
  constructor() {
    this.binanceBaseUrl = 'https://api.binance.com';
    this.cache = new Map();
    this.cacheTimeout = 60000; // 1 minute cache
  }

  async fetchCryptoData(symbol, timeframe = null) {
    const cacheKey = `${symbol}-${timeframe || 'all'}`;

    // Check cache first
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < this.cacheTimeout) {
        return cached.data;
      }
    }

    try {
      const timeframes = timeframe ? [timeframe] : ['15m', '1h', '4h', '1d', '1w', '1M'];
      const promises = timeframes.map(tf => this.fetchKlineData(symbol, tf));
      const results = await Promise.all(promises);

      const data = {
        symbol,
        currentPrice: null,
        priceChange24h: null,
        priceChangePercent24h: null,
        volume24h: null,
        timeframes: {}
      };

      // Get 24h ticker data
      const ticker = await this.getTickerData(symbol);
      if (ticker) {
        data.currentPrice = parseFloat(ticker.lastPrice);
        data.priceChange24h = parseFloat(ticker.priceChange);
        data.priceChangePercent24h = parseFloat(ticker.priceChangePercent);
        data.volume24h = parseFloat(ticker.volume);
      }

      // Process kline data
      timeframes.forEach((tf, index) => {
        data.timeframes[tf] = results[index];
      });

      // Cache the result
      this.cache.set(cacheKey, {
        data,
        timestamp: Date.now()
      });

      return data;

    } catch (error) {
      console.error(`Error fetching crypto data for ${symbol}:`, error);
      throw new Error(`Failed to fetch crypto data: ${error.message}`);
    }
  }

  async fetchKlineData(symbol, interval, limit = 500) {
    try {
      const response = await axios.get(`${this.binanceBaseUrl}/api/v3/klines`, {
        params: {
          symbol: `${symbol}USDT`,
          interval,
          limit
        }
      });

      const klines = response.data;

      // Convert to more usable format
      const candles = klines.map(k => ({
        timestamp: parseInt(k[0]),
        open: parseFloat(k[1]),
        high: parseFloat(k[2]),
        low: parseFloat(k[3]),
        close: parseFloat(k[4]),
        volume: parseFloat(k[5]),
        closeTime: parseInt(k[6]),
        quoteVolume: parseFloat(k[7]),
        trades: parseInt(k[8]),
        takerBuyVolume: parseFloat(k[9]),
        takerBuyQuoteVolume: parseFloat(k[10])
      }));

      return {
        interval,
        candles,
        currentPrice: candles[candles.length - 1].close,
        high24h: Math.max(...candles.slice(-96).map(c => c.high)),
        low24h: Math.min(...candles.slice(-96).map(c => c.low)),
        volume24h: candles.slice(-96).reduce((sum, c) => sum + c.volume, 0)
      };

    } catch (error) {
      console.error(`Error fetching kline data for ${symbol} ${interval}:`, error);
      throw error;
    }
  }

  async getTickerData(symbol) {
    try {
      const response = await axios.get(`${this.binanceBaseUrl}/api/v3/ticker/24hr`, {
        params: {
          symbol: `${symbol}USDT`
        }
      });
      return response.data;
    } catch (error) {
      console.error(`Error fetching ticker data for ${symbol}:`, error);
      return null;
    }
  }

  calculateTechnicalIndicators(cryptoData) {
    const analysis = {
      rsi: null,
      macd: null,
      sma20: null,
      ema20: null,
      bollingerBands: null,
      timeframes: {}
    };

    // Calculate for each timeframe
    Object.keys(cryptoData.timeframes).forEach(timeframe => {
      const tfData = cryptoData.timeframes[timeframe];
      const closes = tfData.candles.map(c => c.close);
      const highs = tfData.candles.map(c => c.high);
      const lows = tfData.candles.map(c => c.low);

      if (closes.length >= 14) {
        // RSI
        const rsiValues = RSI.calculate({
          values: closes,
          period: 14
        });

        // MACD
        const macdValues = MACD.calculate({
          values: closes,
          fastPeriod: 12,
          slowPeriod: 26,
          signalPeriod: 9
        });

        // Simple Moving Average
        const sma20Values = SMA.calculate({
          values: closes,
          period: 20
        });

        // Exponential Moving Average
        const ema20Values = EMA.calculate({
          values: closes,
          period: 20
        });

        // Bollinger Bands
        const bbValues = BollingerBands.calculate({
          values: closes,
          period: 20,
          stdDev: 2
        });

        analysis.timeframes[timeframe] = {
          rsi: rsiValues[rsiValues.length - 1] || null,
          macd: macdValues[macdValues.length - 1] || null,
          sma20: sma20Values[sma20Values.length - 1] || null,
          ema20: ema20Values[ema20Values.length - 1] || null,
          bollingerBands: bbValues[bbValues.length - 1] || null,
          currentPrice: tfData.currentPrice,
          volume: tfData.volume24h
        };
      }
    });

    // Get 1D values for main analysis
    const dailyData = analysis.timeframes['1d'];
    if (dailyData) {
      analysis.rsi = dailyData.rsi;
      analysis.macd = dailyData.macd;
      analysis.sma20 = dailyData.sma20;
      analysis.ema20 = dailyData.ema20;
      analysis.bollingerBands = dailyData.bollingerBands;
    }

    return analysis;
  }

  generateSignals(technicalAnalysis) {
    const signals = {
      overallSignal: 'HOLD',
      overallTrend: 'NEUTRAL',
      signals: {
        rsi: 'NEUTRAL',
        macd: 'NEUTRAL',
        ma: 'NEUTRAL',
        volume: 'NEUTRAL'
      },
      confidence: 0
    };

    let bullishCount = 0;
    let bearishCount = 0;

    // RSI Signal
    if (technicalAnalysis.rsi) {
      if (technicalAnalysis.rsi < 30) {
        signals.signals.rsi = 'BULLISH';
        bullishCount++;
      } else if (technicalAnalysis.rsi > 70) {
        signals.signals.rsi = 'BEARISH';
        bearishCount++;
      }
    }

    // MACD Signal
    if (technicalAnalysis.macd) {
      if (technicalAnalysis.macd.histogram > 0 && technicalAnalysis.macd.MACD > technicalAnalysis.macd.signal) {
        signals.signals.macd = 'BULLISH';
        bullishCount++;
      } else if (technicalAnalysis.macd.histogram < 0) {
        signals.signals.macd = 'BEARISH';
        bearishCount++;
      }
    }

    // Moving Average Signal
    if (technicalAnalysis.ema20 && technicalAnalysis.sma20) {
      if (technicalAnalysis.ema20 > technicalAnalysis.sma20) {
        signals.signals.ma = 'BULLISH';
        bullishCount++;
      } else {
        signals.signals.ma = 'BEARISH';
        bearishCount++;
      }
    }

    // Determine overall signal
    if (bullishCount > bearishCount) {
      signals.overallSignal = 'BUY 🟢';
      signals.overallTrend = 'BULLISH';
      signals.confidence = (bullishCount / 3) * 100;
    } else if (bearishCount > bullishCount) {
      signals.overallSignal = 'SELL 🔴';
      signals.overallTrend = 'BEARISH';
      signals.confidence = (bearishCount / 3) * 100;
    }

    return signals;
  }

  findKeyLevels(cryptoData) {
    const levels = {
      support: [],
      resistance: []
    };

    // Use daily data for key levels
    const dailyData = cryptoData.timeframes['1d'];
    if (!dailyData) return levels;

    const candles = dailyData.candles;
    const recentCandles = candles.slice(-50); // Last 50 days

    // Find swing highs and lows
    for (let i = 2; i < recentCandles.length - 2; i++) {
      const current = recentCandles[i];

      // Potential resistance (swing high)
      if (current.high > recentCandles[i - 1].high &&
          current.high > recentCandles[i - 2].high &&
          current.high > recentCandles[i + 1].high &&
          current.high > recentCandles[i + 2].high) {
        if (!levels.resistance.includes(current.high)) {
          levels.resistance.push(current.high);
        }
      }

      // Potential support (swing low)
      if (current.low < recentCandles[i - 1].low &&
          current.low < recentCandles[i - 2].low &&
          current.low < recentCandles[i + 1].low &&
          current.low < recentCandles[i + 2].low) {
        if (!levels.support.includes(current.low)) {
          levels.support.push(current.low);
        }
      }
    }

    // Sort and limit to 3 levels each
    levels.resistance = levels.resistance
      .sort((a, b) => b - a)
      .slice(0, 3);

    levels.support = levels.support
      .sort((a, b) => a - b)
      .slice(0, 3);

    return levels;
  }

  calculateRiskMetrics(technicalAnalysis) {
    const metrics = {
      volatility: 'UNKNOWN',
      riskLevel: 'MEDIUM',
      suggestedStopLoss: null,
      suggestedTakeProfit: null
    };

    if (technicalAnalysis.bollingerBands && technicalAnalysis.rsi) {
      // Volatility assessment based on Bollinger Bands width
      const bb = technicalAnalysis.bollingerBands;
      const width = ((bb.upper - bb.lower) / bb.middle) * 100;

      if (width > 10) {
        metrics.volatility = 'HIGH';
        metrics.riskLevel = 'HIGH';
      } else if (width > 5) {
        metrics.volatility = 'MEDIUM';
        metrics.riskLevel = 'MEDIUM';
      } else {
        metrics.volatility = 'LOW';
        metrics.riskLevel = 'LOW';
      }

      // Suggested stop loss and take profit based on volatility
      if (technicalAnalysis.rsi < 30) {
        metrics.suggestedStopLoss = 3; // 3%
        metrics.suggestedTakeProfit = 8; // 8%
      } else if (technicalAnalysis.rsi > 70) {
        metrics.suggestedStopLoss = 2;
        metrics.suggestedTakeProfit = 5;
      } else {
        metrics.suggestedStopLoss = 2.5;
        metrics.suggestedTakeProfit = 6;
      }
    }

    return metrics;
  }

  async getAIAnalysis(data) {
    // This would integrate with Claude AI
    // For now, return mock analysis
    return {
      recommendation: 'HOLD',
      analysis: 'Current market conditions suggest waiting for clearer signals. The technical indicators show mixed signals with no strong directional bias.',
      confidence: 65
    };
  }
}

module.exports = new CryptoService();