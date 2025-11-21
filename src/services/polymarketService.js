const axios = require('axios');

class PolymarketService {
  constructor() {
    this.baseUrl = 'https://gamma-api.polymarket.com';
    this.cache = new Map();
    this.cacheTimeout = 300000; // 5 minutes cache
  }

  async getSentimentData(symbol) {
    const cacheKey = `sentiment-${symbol}`;

    // Check cache
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < this.cacheTimeout) {
        return cached.data;
      }
    }

    try {
      // Map symbol to search terms
      const searchTerm = this.mapSymbolToSearchTerm(symbol);

      // Fetch markets related to the symbol
      const markets = await this.fetchRelatedMarkets(searchTerm);

      // Calculate sentiment score
      const sentimentData = this.calculateSentiment(markets, symbol);

      // Cache the result
      this.cache.set(cacheKey, {
        data: sentimentData,
        timestamp: Date.now()
      });

      return sentimentData;

    } catch (error) {
      console.error(`Error fetching sentiment for ${symbol}:`, error);
      // Return neutral sentiment on error
      return {
        score: 50,
        confidence: 0,
        sources: 0,
        markets: [],
        trend: 'NEUTRAL'
      };
    }
  }

  async fetchRelatedMarkets(searchTerm) {
    try {
      // Search for markets
      const response = await axios.get(`${this.baseUrl}/markets`, {
        params: {
          limit: 50,
          active: true
        }
      });

      // Filter markets related to our search term
      const markets = response.data.filter(market =>
        market.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
        market.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        market.tags?.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );

      // Fetch price data for each market
      const marketsWithPrices = await Promise.all(
        markets.map(async (market) => {
          try {
            const priceData = await this.getMarketPrice(market.id);
            return {
              ...market,
              price: priceData.price,
              volume: priceData.volume24h,
              liquidity: priceData.liquidity
            };
          } catch (e) {
            return {
              ...market,
              price: 0,
              volume: 0,
              liquidity: 0
            };
          }
        })
      );

      return marketsWithPrices;

    } catch (error) {
      console.error('Error fetching markets:', error);
      return [];
    }
  }

  async getMarketPrice(marketId) {
    try {
      const response = await axios.get(`${this.baseUrl}/markets/${marketId}`);
      return {
        price: response.data.price || 0,
        volume24h: response.data.volume24h || 0,
        liquidity: response.data.liquidity || 0
      };
    } catch (error) {
      console.error(`Error fetching price for market ${marketId}:`, error);
      return {
        price: 0,
        volume24h: 0,
        liquidity: 0
      };
    }
  }

  calculateSentiment(markets, symbol) {
    if (markets.length === 0) {
      return {
        score: 50,
        confidence: 0,
        sources: 0,
        markets: [],
        trend: 'NEUTRAL',
        analysis: 'No prediction markets found for this asset'
      };
    }

    let totalScore = 0;
    let totalVolume = 0;
    let bullishMarkets = 0;
    let bearishMarkets = 0;

    // Analyze each market
    markets.forEach(market => {
      const sentiment = this.analyzeMarketSentiment(market, symbol);
      const weight = Math.log(market.volume + 1) + 1; // Log volume weighting

      totalScore += sentiment.score * weight;
      totalVolume += weight;

      if (sentiment.direction === 'BULLISH') bullishMarkets++;
      else if (sentiment.direction === 'BEARISH') bearishMarkets++;
    });

    // Calculate weighted average
    const weightedScore = totalScore / totalVolume;
    const confidence = Math.min((totalVolume / markets.length) * 10, 100);

    // Determine trend
    let trend = 'NEUTRAL';
    if (weightedScore > 60) trend = 'BULLISH';
    else if (weightedScore < 40) trend = 'BEARISH';

    // Top markets by volume
    const topMarkets = markets
      .sort((a, b) => b.volume - a.volume)
      .slice(0, 3)
      .map(m => ({
        question: m.question,
        price: (m.price * 100).toFixed(1) + '%',
        volume: this.formatVolume(m.volume)
      }));

    return {
      score: Math.round(weightedScore),
      confidence: Math.round(confidence),
      sources: markets.length,
      bullishMarkets,
      bearishMarkets,
      trend,
      markets: topMarkets,
      analysis: this.generateSentimentAnalysis(weightedScore, markets.length, bullishMarkets, bearishMarkets)
    };
  }

  analyzeMarketSentiment(market, symbol) {
    const question = market.question.toLowerCase();
    const description = (market.description || '').toLowerCase();
    const price = market.price || 0;

    // Bullish keywords
    const bullishKeywords = [
      'reach', 'exceed', 'above', 'higher', 'rise', 'increase', 'gain', 'bull',
      'moon', 'pump', 'surge', 'rally', 'breakout', ' ATH', 'all-time high'
    ];

    // Bearish keywords
    const bearishKeywords = [
      'fall', 'below', 'lower', 'drop', 'decrease', 'decline', 'bear',
      'crash', 'dump', 'plunge', 'collapse', 'breakdown'
    ];

    let direction = 'NEUTRAL';
    let scoreModifier = 0;

    // Check for directional keywords
    bullishKeywords.forEach(keyword => {
      if (question.includes(keyword) || description.includes(keyword)) {
        direction = 'BULLISH';
      }
    });

    bearishKeywords.forEach(keyword => {
      if (question.includes(keyword) || description.includes(keyword)) {
        direction = 'BEARISH';
      }
    });

    // Calculate score based on market price and direction
    if (direction === 'BULLISH') {
      scoreModifier = price * 30; // Up to 30 points
    } else if (direction === 'BEARISH') {
      scoreModifier = (1 - price) * 30; // Up to 30 points
    }

    // Base score is 50, modified by market sentiment
    return {
      direction,
      score: 50 + scoreModifier
    };
  }

  mapSymbolToSearchTerm(symbol) {
    const mapping = {
      'BTC': 'Bitcoin',
      'ETH': 'Ethereum',
      'SOL': 'Solana',
      'ADA': 'Cardano',
      'DOT': 'Polkadot',
      'MATIC': 'Polygon',
      'AVAX': 'Avalanche',
      'LINK': 'Chainlink',
      'UNI': 'Uniswap',
      'ATOM': 'Cosmos'
    };

    return mapping[symbol] || symbol;
  }

  formatVolume(volume) {
    if (volume >= 1000000) {
      return `$${(volume / 1000000).toFixed(1)}M`;
    } else if (volume >= 1000) {
      return `$${(volume / 1000).toFixed(1)}K`;
    }
    return `$${volume.toFixed(0)}`;
  }

  generateSentimentAnalysis(score, totalMarkets, bullish, bearish) {
    const sentiment = score > 60 ? 'optimistic' : score < 40 ? 'pessimistic' : 'neutral';

    let analysis = `Polymarket sentiment is ${sentiment} with `;
    analysis += `${totalMarkets} active prediction markets. `;

    if (bullish > bearish) {
      analysis += `${bullish} markets show bullish sentiment while ${bearish} show bearish sentiment. `;
    } else if (bearish > bullish) {
      analysis += `${bearish} markets show bearish sentiment while ${bullish} show bullish sentiment. `;
    }

    analysis += `Crowd wisdom suggests ${sentiment === 'optimistic' ? 'potential upside' : sentiment === 'pessimistic' ? 'potential downside' : 'sideways movement'}.`;

    return analysis;
  }
}

module.exports = new PolymarketService();