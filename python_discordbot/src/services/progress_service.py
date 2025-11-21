import discord
import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProgressMessage:
    """Container for progress message data"""
    interaction: discord.Interaction
    message: Optional[discord.Message]
    title: str
    max_steps: int
    current_step: int = 0
    start_time: float = 0
    last_update: float = 0
    steps_log: list = None

    def __post_init__(self):
        if self.steps_log is None:
            self.steps_log = []

class ProgressService:
    """Service for managing progress messages with async updates"""

    UPDATE_COOLDOWN = 2.0  # Minimum seconds between updates

    def __init__(self):
        self.active_progress: Dict[str, ProgressMessage] = {}

    async def create_progress(self, interaction: discord.Interaction,
                            title: str, max_steps: int = 5) -> ProgressMessage:
        """Create a new progress tracker"""
        progress_id = f"{interaction.user.id}_{int(time.time())}"

        # Create initial embed
        embed = discord.Embed(
            title=f"🔄 {title}",
            description=self._create_progress_bar(0, max_steps),
            color=discord.Color.blue()
        )

        # Add initial info
        embed.add_field(
            name="Status",
            value="Initializing...",
            inline=False
        )

        embed.add_field(
            name="Progress",
            value=f"0/{max_steps} steps completed",
            inline=True
        )

        embed.add_field(
            name="ETA",
            value="Calculating...",
            inline=True
        )

        embed.set_footer(
            text=f"Started by {interaction.user.display_name} • {interaction.guild.name}"
        )
        embed.timestamp = discord.utils.utcnow()

        # Send initial message
        await interaction.response.defer()
        message = await interaction.followup.send(embed=embed)

        # Create progress object
        progress = ProgressMessage(
            interaction=interaction,
            message=message,
            title=title,
            max_steps=max_steps,
            start_time=time.time()
        )

        self.active_progress[progress_id] = progress
        return progress

    async def update(self, progress: ProgressMessage,
                    step: int, message: str = None,
                    detail: str = None) -> None:
        """Update progress message"""
        progress.current_step = step
        current_time = time.time()

        # Check cooldown
        if current_time - progress.last_update < self.UPDATE_COOLDOWN:
            # Store in log but don't update message
            progress.steps_log.append({
                'step': step,
                'time': current_time,
                'message': message,
                'detail': detail
            })
            return

        try:
            # Calculate progress percentage
            progress_percent = (step / progress.max_steps) * 100

            # Estimate time remaining
            elapsed_time = current_time - progress.start_time
            if step > 0:
                avg_time_per_step = elapsed_time / step
                remaining_steps = progress.max_steps - step
                eta_seconds = remaining_steps * avg_time_per_step
                eta = self._format_time(eta_seconds)
            else:
                eta = "Calculating..."

            # Create updated embed
            embed = discord.Embed(
                title=f"🔄 {progress.title}",
                description=self._create_progress_bar(step, progress.max_steps),
                color=discord.Color.blue()
            )

            # Main status message
            status_text = message or f"Processing step {step}..."
            embed.add_field(
                name="Status",
                value=status_text,
                inline=False
            )

            # Progress info
            embed.add_field(
                name="Progress",
                value=f"{step}/{progress.max_steps} steps ({progress_percent:.1f}%)",
                inline=True
            )

            embed.add_field(
                name="ETA",
                value=eta,
                inline=True
            )

            # Add detail if provided
            if detail:
                embed.add_field(
                    name="Details",
                    value=detail[:1024],  # Discord field limit
                    inline=False
                )

            # Add recent steps from log
            if len(progress.steps_log) > 0:
                recent_steps = progress.steps_log[-3:]
                steps_text = "\n".join([
                    f"• Step {s['step']}: {s['message'] or 'Processing...'}"
                    for s in recent_steps
                ])
                embed.add_field(
                    name="Recent Activity",
                    value=steps_text[:1024],
                    inline=False
                )

            # Update footer with elapsed time
            elapsed = self._format_time(elapsed_time)
            embed.set_footer(
                text=f"Started by {progress.interaction.user.display_name} • "
                     f"Elapsed: {elapsed} • {progress.interaction.guild.name}"
            )
            embed.timestamp = discord.utils.utcnow()

            # Edit the message
            await progress.message.edit(embed=embed)

            # Update tracking
            progress.last_update = current_time
            progress.steps_log.append({
                'step': step,
                'time': current_time,
                'message': message,
                'detail': detail
            })

        except discord.errors.NotFound:
            logger.warning("Progress message not found - may have been deleted")
        except Exception as e:
            logger.error(f"Error updating progress message: {str(e)}")

    async def finalize(self, progress: ProgressMessage,
                      embed: discord.Embed = None,
                      message: str = None,
                      error: bool = False) -> None:
        """Finalize progress with success or error message"""
        try:
            if error:
                # Error embed
                embed = discord.Embed(
                    title="❌ Analysis Failed",
                    description=message or "An error occurred during analysis",
                    color=discord.Color.red()
                )
            elif embed:
                # Success with custom embed
                pass
            else:
                # Default success embed
                elapsed = time.time() - progress.start_time
                embed = discord.Embed(
                    title="✅ Analysis Complete",
                    description=message or "Analysis completed successfully",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Completed in",
                    value=self._format_time(elapsed),
                    inline=True
                )
                embed.add_field(
                    name="Total Steps",
                    value=f"{progress.current_step}/{progress.max_steps}",
                    inline=True
                )

            # Update footer
            embed.set_footer(
                text=f"Requested by {progress.interaction.user.display_name} • "
                     f"{progress.interaction.guild.name}"
            )
            embed.timestamp = discord.utils.utcnow()

            # Final edit
            await progress.message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Error finalizing progress message: {str(e)}")

        finally:
            # Clean up
            self.active_progress.pop(
                f"{progress.interaction.user.id}_{int(progress.start_time)}",
                None
            )

    async def handle_error(self, progress: ProgressMessage,
                          error: Exception, context: str = None) -> None:
        """Handle errors in progress updates"""
        error_message = str(error)

        # Create user-friendly error message
        if "timeout" in error_message.lower():
            user_message = "⏱️ Request timed out. Please try again."
        elif "rate limit" in error_message.lower():
            user_message = "⚠️ Rate limit exceeded. Please wait and try again."
        elif "not found" in error_message.lower():
            user_message = f"🔍 {context or 'Data'} not found."
        else:
            user_message = "💥 An unexpected error occurred. Please try again later."

        await self.finalize(
            progress,
            message=user_message,
            error=True
        )

        # Log the full error
        logger.error(f"Error in {context or 'operation'}: {error_message}", exc_info=True)

    def _create_progress_bar(self, current: int, max_steps: int,
                           length: int = 10) -> str:
        """Create ASCII progress bar"""
        if max_steps == 0:
            percentage = 0
        else:
            percentage = (current / max_steps) * 100

        filled = int((percentage / 100) * length)
        empty = length - filled

        # Choose bar characters
        filled_char = "█"
        empty_char = "░"

        bar = filled_char * filled + empty_char * empty
        percentage_text = f"{percentage:.0f}%"

        return f"```\n{bar} {percentage_text}\n```"

    def _format_time(self, seconds: float) -> str:
        """Format seconds into human readable time"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m {seconds % 60:.0f}s"
        else:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{hours:.0f}h {minutes:.0f}m"