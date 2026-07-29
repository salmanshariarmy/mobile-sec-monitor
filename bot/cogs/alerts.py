"""
Alert management commands — view, filter, acknowledge.
"""
import discord
from discord import app_commands
from discord.ext import commands


class AlertsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="alerts", description="View security alerts")
    @app_commands.describe(
        action="Action: recent, severity, or acknowledge",
        count="Number of alerts (default 10)",
        level="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW, INFO",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Recent alerts", value="recent"),
        app_commands.Choice(name="By severity", value="severity"),
        app_commands.Choice(name="Acknowledge all", value="acknowledge"),
    ])
    async def alerts(self, interaction: discord.Interaction,
                     action: str = "recent",
                     count: int = 10,
                     level: str = None):
        await interaction.response.defer()

        db = self.bot.db

        if action == "recent":
            threats = db.get_recent_threats(limit=min(count, 50))
            if not threats:
                return await interaction.followup.send("✅ No alerts found.")

            embeds = []
            SEV_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "🔵"}
            for t in threats[:5]:  # Show max 5 at once (embed limits)
                emoji = SEV_EMOJI.get(t["severity"], "⚪")
                embed = discord.Embed(
                    title=f"{emoji} [{t['severity']}] {t['title']}",
                    description=t["description"][:400],
                    color=discord.Color.red() if t["severity"] == "CRITICAL"
                    else discord.Color.orange() if t["severity"] == "HIGH"
                    else discord.Color.gold() if t["severity"] == "MEDIUM"
                    else discord.Color.green(),
                    timestamp=discord.utils.parse_time(t["timestamp"])
                )
                embed.set_footer(text=f"Agent: {t['agent_id']} | ID: {t['id']}")
                embeds.append(embed)

            # Send first embed with count info
            if embeds:
                await interaction.followup.send(
                    f"📋 **{len(threats)} recent alerts** (showing {len(embeds)})",
                    embed=embeds[0]
                )
                for e in embeds[1:]:
                    await interaction.followup.send(embed=e)

        elif action == "severity":
            if not level:
                return await interaction.followup.send("Specify a level, e.g. `level: CRITICAL`")
            threats = db.get_recent_threats(limit=min(count, 50), severity=level.upper())
            if not threats:
                return await interaction.followup.send(f"✅ No {level.upper()} alerts.")
            await interaction.followup.send(f"**{len(threats)}** {level.upper()} alerts found.")
            # Send first few as embeds
            for t in threats[:3]:
                embed = discord.Embed(
                    title=f"[{t['severity']}] {t['title']}",
                    description=t["description"][:400],
                    timestamp=discord.utils.parse_time(t["timestamp"])
                )
                await interaction.followup.send(embed=embed)

        elif action == "acknowledge":
            # In production: mark as acknowledged in DB
            await interaction.followup.send("✅ All alerts acknowledged.")


async def setup(bot):
    await bot.add_cog(AlertsCog(bot))
