import discord
from discord import app_commands
from discord.ext import commands

class AlertsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="alerts", description="View recent alerts")
    @app_commands.describe(filter_type="recent, severity, or agent", value="count, level, or ID")
    @app_commands.choices(filter_type=[
        app_commands.Choice(name="recent", value="recent"),
        app_commands.Choice(name="severity", value="severity"),
        app_commands.Choice(name="agent", value="agent"),
    ])
    async def alerts(self, interaction: discord.Interaction, filter_type: str = "recent", value: str = "10"):
        await interaction.response.defer()
        try:
            count = int(value) if filter_type == "recent" else 25
            severity = value.upper() if filter_type == "severity" else None
            agent_id = value if filter_type == "agent" else None
            alerts = self.bot.db.get_alerts(limit=min(count, 100), severity=severity, agent_id=agent_id)
            if not alerts:
                await interaction.followup.send("✅ No alerts found.", ephemeral=True)
                return
            embed = discord.Embed(title=f"🛡️ Alerts ({len(alerts)})", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            for a in alerts[:10]:
                sev = a.get("severity", "MEDIUM")
                emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
                embed.add_field(name=f"{emoji} [{sev}] {a.get('title', '?')}",
                              value=f"`{a.get('timestamp', '')[:16]}` · {a.get('agent_id', '?')}", inline=False)
            if len(alerts) > 10:
                embed.set_footer(text=f"Showing 10 of {len(alerts)}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AlertsCog(bot))
