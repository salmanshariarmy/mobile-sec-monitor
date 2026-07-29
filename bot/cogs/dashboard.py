"""
Dashboard and analytics commands.
"""
import discord
from discord import app_commands
from discord.ext import commands


class DashboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="System health overview")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        db = self.bot.db

        # Summary stats
        summary_24h = db.get_threat_summary(hours=24)
        summary_7d = db.get_threat_summary(hours=168)
        agents = db.get_agents()
        recent = db.get_recent_threats(limit=1)

        embed = discord.Embed(
            title="🛡️ Mobile Security Monitor — Status",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(name="🤖 Bot Status", value="✅ Online", inline=True)
        embed.add_field(name="📡 Connected Agents", value=str(len(agents)), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer

        embed.add_field(
            name="📊 Threats (24h)",
            value=f"Total: {summary_24h['total']}\n"
                  f"🔴 Critical: {summary_24h['CRITICAL']}\n"
                  f"🟠 High: {summary_24h['HIGH']}\n"
                  f"🟡 Medium: {summary_24h['MEDIUM']}",
            inline=True
        )
        embed.add_field(
            name="📊 Threats (7d)",
            value=f"Total: {summary_7d['total']}\n"
                  f"🔴 Critical: {summary_7d['CRITICAL']}\n"
                  f"🟠 High: {summary_7d['HIGH']}\n"
                  f"🟡 Medium: {summary_7d['MEDIUM']}",
            inline=True
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        if recent:
            last = recent[0]
            embed.add_field(
                name="🕐 Last Alert",
                value=f"[{last['severity']}] {last['title']}\n{last['description'][:100]}",
                inline=False
            )

        embed.set_footer(text=f"Agent API: {self.bot.http_host}:{self.bot.http_port}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="summary", description="Threat summary for last N hours")
    @app_commands.describe(hours="Hours to look back (default 24)")
    async def summary(self, interaction: discord.Interaction, hours: int = 24):
        await interaction.response.defer()
        db = self.bot.db
        summary = db.get_threat_summary(hours=hours)

        embed = discord.Embed(
            title=f"📈 Threat Summary — Last {hours}h",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🔴 Critical", value=str(summary["CRITICAL"]), inline=True)
        embed.add_field(name="🟠 High", value=str(summary["HIGH"]), inline=True)
        embed.add_field(name="🟡 Medium", value=str(summary["MEDIUM"]), inline=True)
        embed.add_field(name="🟢 Low", value=str(summary["LOW"]), inline=True)
        embed.add_field(name="🔵 Info", value=str(summary["INFO"]), inline=True)
        embed.add_field(name="📊 Total", value=str(summary["total"]), inline=True)
        embed.set_footer(text="Severity breakdown")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="dashboard", description="Interactive threat dashboard link")
    async def dashboard(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📊 Web Dashboard",
            description="Open the web dashboard in your browser for full analytics.\n\n"
                        "**Comming soon:** Real-time graphs, agent maps, threat timeline.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Local Dashboard", value="http://localhost:8080", inline=True)
        # In production: link to your actual hosted dashboard
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(DashboardCog(bot))
