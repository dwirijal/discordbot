const { EmbedBuilder } = require('discord.js');

class ProgressMessage {
  constructor(interaction) {
    this.interaction = interaction;
    this.message = null;
    this.startTime = Date.now();
    this.currentStep = 0;
    this.totalSteps = 8;
  }

  async initialize(initialMessage) {
    // Create initial message with defer
    await this.interaction.deferReply();

    // Create progress embed
    const embed = new EmbedBuilder()
      .setColor(0x0099ff)
      .setTitle('🔄 Crypto Analysis in Progress')
      .setDescription(initialMessage + '\n\n' + this.createProgressBar(0))
      .setTimestamp();

    // Send initial message
    this.message = await this.interaction.editReply({ embeds: [embed] });
    return this.message;
  }

  async update(step, totalSteps, message) {
    this.currentStep = step;
    this.totalSteps = totalSteps;

    const elapsed = Date.now() - this.startTime;
    const avgTimePerStep = elapsed / step;
    const remainingSteps = totalSteps - step;
    const estimatedTime = remainingSteps * avgTimePerStep;

    const embed = new EmbedBuilder()
      .setColor(0x0099ff)
      .setTitle('🔄 Crypto Analysis in Progress')
      .setDescription(
        `${message}\n\n` +
        this.createProgressBar(step, totalSteps) +
        `\n\n📊 Step: ${step}/${totalSteps} | ` +
        `⏱️ ETA: ${this.formatTime(estimatedTime)}`
      )
      .setTimestamp();

    try {
      // Rate limiting: only update every 2 seconds minimum
      if (!this.lastUpdate || Date.now() - this.lastUpdate > 2000) {
        await this.interaction.editReply({ embeds: [embed] });
        this.lastUpdate = Date.now();
      }
    } catch (error) {
      console.error('Error updating progress message:', error);
    }
  }

  async finalize(content) {
    const totalTime = Date.now() - this.startTime;

    if (content.embeds && content.embeds.length > 0) {
      // Add execution time footer
      const embed = content.embeds[0];
      embed.setFooter({
        text: `Analysis completed in ${this.formatTime(totalTime)} | ⚠️ Not financial advice`,
        iconURL: this.interaction.client.user.displayAvatarURL()
      });
    }

    try {
      await this.interaction.editReply(content);
    } catch (error) {
      console.error('Error finalizing progress message:', error);
    }
  }

  createProgressBar(current, total = this.totalSteps) {
    const progress = Math.round((current / total) * 10);
    const empty = '░';
    const filled = '█';

    let bar = '';
    for (let i = 0; i < 10; i++) {
      if (i < progress) {
        bar += filled;
      } else {
        bar += empty;
      }
    }

    const percentage = Math.round((current / total) * 100);
    return `\`\`\`\n${bar} ${percentage}%\n\`\`\``;
  }

  formatTime(ms) {
    const seconds = Math.floor(ms / 1000);

    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  }

  async addStepInfo(title, value, inline = false) {
    // This could be used to add detailed step information
    // Implementation depends on specific requirements
  }
}

module.exports = ProgressMessage;