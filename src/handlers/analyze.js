const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const cryptoService = require('../services/cryptoService');
const polymarketService = require('../services/polymarketService');
const ProgressMessage = require('../utils/progressMessage');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('analyze')
    .setDescription('Analyze cryptocurrency technical analysis')
    .addStringOption(option =>
      option.setName('symbol')
        .setDescription('Cryptocurrency symbol (e.g., BTC, ETH)')
        .setRequired(true)
    )
    .addStringOption(option =>
      option.setName('timeframe')
        .setDescription('Specific timeframe to analyze')
        .addChoices(
          { name: '15 minutes', value: '15m' },
          { name: '1 hour', value: '1h' },
          { name: '4 hours', value: '4h' },
          { name: '1 day', value: '1d' },
          { name: '1 week', value: '1w' },
          { name: '1 month', value: '1M' }
        )
    ),

  async execute(interaction) {
    const symbol = interaction.options.getString('symbol').toUpperCase();
    const timeframe = interaction.options.getString('timeframe');

    // Initialize progress message
    const progress = new ProgressMessage(interaction);
    await progress.initialize(`🔄 Analyzing ${symbol}/USDT...`);

    try {
      // Step 1: Fetch crypto data (with progress updates)
      await progress.update(1, 8, '📊 Fetching price data from Binance...');
      const cryptoData = await cryptoService.fetchCryptoData(symbol, timeframe);

      await progress.update(2, 8, '📈 Calculating technical indicators...');
      const technicalAnalysis = cryptoService.calculateTechnicalIndicators(cryptoData);

      await progress.update(3, 8, '🔍 Analyzing market sentiment...');
      const sentimentData = await polymarketService.getSentimentData(symbol);

      await progress.update(4, 8, '🤖 Running AI analysis...');
      const aiAnalysis = await cryptoService.getAIAnalysis({
        symbol,
        technicalAnalysis,
        sentimentData,
        timeframe
      });

      await progress.update(5, 8, '📊 Generating trading signals...');
      const signals = cryptoService.generateSignals(technicalAnalysis);

      await progress.update(6, 8, '💎 Identifying key levels...');
      const keyLevels = cryptoService.findKeyLevels(cryptoData);

      await progress.update(7, 8, '🎯 Calculating risk metrics...');
      const riskMetrics = cryptoService.calculateRiskMetrics(technicalAnalysis);

      await progress.update(8, 8, '✅ Finalizing analysis...');

      // Create final embed
      const embed = new EmbedBuilder()
        .setTitle(`🔍 ${symbol}/USDT Technical Analysis`)
        .setColor(getTrendColor(signals.overallTrend))
        .setTimestamp()
        .addFields(
          {
            name: '📊 Current Price',
            value: `**$${cryptoData.currentPrice?.toLocaleString() || 'N/A'}**`,
            inline: true
          },
          {
            name: '📈 24h Change',
            value: `${cryptoData.priceChange24h >= 0 ? '🟢' : '🔴'} ${cryptoData.priceChangePercent24h?.toFixed(2) || 'N/A'}%`,
            inline: true
          },
          {
            name: '💎 Overall Signal',
            value: signals.overallSignal,
            inline: true
          },
          {
            name: '🎯 Key Support',
            value: keyLevels.support.map(level => `$${level}`).join(', '),
            inline: true
          },
          {
            name: '🎯 Key Resistance',
            value: keyLevels.resistance.map(level => `$${level}`).join(', '),
            inline: true
          },
          {
            name: '⚡ RSI (14)',
            value: `${technicalAnalysis.rsi?.toFixed(2) || 'N/A'} ${getRSIEmoji(technicalAnalysis.rsi)}`,
            inline: true
          },
          {
            name: '📊 MACD',
            value: getMACDSignal(technicalAnalysis.macd),
            inline: true
          },
          {
            name: '💰 Sentiment Score',
            value: `${sentimentData.score}/100 ${getSentimentEmoji(sentimentData.score)}`,
            inline: true
          },
          {
            name: '🤖 AI Recommendation',
            value: aiAnalysis.recommendation || 'N/A',
            inline: false
          },
          {
            name: '📝 AI Analysis',
            value: aiAnalysis.analysis || 'N/A',
            inline: false
          }
        );

      // Add timeframe specific data
      if (timeframe) {
        embed.addFields({
          name: `⏰ ${timeframe.toUpperCase()} Analysis`,
          value: formatTimeframeAnalysis(technicalAnalysis, timeframe),
          inline: false
        });
      }

      // Add risk disclaimer
      embed.setFooter({
        text: '⚠️ Not financial advice. Always do your own research.',
        iconURL: client.user.displayAvatarURL()
      });

      // Update with final result
      await progress.finalize({ embeds: [embed] });

    } catch (error) {
      console.error('Analysis error:', error);
      await progress.finalize({
        content: `❌ Error analyzing ${symbol}: ${error.message}`,
        embeds: []
      });
    }
  }
};

function getTrendColor(trend) {
  switch (trend?.toLowerCase()) {
    case 'bullish': return 0x00ff00;
    case 'bearish': return 0xff0000;
    case 'neutral': return 0xffff00;
    default: return 0x0099ff;
  }
}

function getRSIEmoji(rsi) {
  if (rsi >= 70) return '🔴 (Overbought)';
  if (rsi <= 30) return '🟢 (Oversold)';
  return '🟡 (Neutral)';
}

function getMACDSignal(macd) {
  if (!macd) return 'N/A';
  return macd.histogram > 0 ? '🟢 Bullish' : '🔴 Bearish';
}

function getSentimentEmoji(score) {
  if (score >= 70) return '🚀';
  if (score >= 50) return '😊';
  if (score >= 30) return '😐';
  return '😰';
}

function formatTimeframeAnalysis(analysis, timeframe) {
  const tf = analysis[timeframe];
  if (!tf) return 'No data available';

  return `RSI: ${tf.rsi?.toFixed(2) || 'N/A'} | ` +
         `MA20: ${tf.ma20?.toFixed(2) || 'N/A'} | ` +
         `Volume: ${formatVolume(tf.volume)}`;
}

function formatVolume(volume) {
  if (!volume) return 'N/A';
  if (volume >= 1e9) return `$${(volume / 1e9).toFixed(2)}B`;
  if (volume >= 1e6) return `$${(volume / 1e6).toFixed(2)}M`;
  if (volume >= 1e3) return `$${(volume / 1e3).toFixed(2)}K`;
  return `$${volume.toFixed(2)}`;
}