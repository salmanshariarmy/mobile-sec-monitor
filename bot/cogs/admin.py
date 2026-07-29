import discord
from discord import app_commands
from discord.ext import commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="System health and stats")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(title="🛡️ Security Monitor — Status", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="🤖 Bot", value=f"{self.bot.user}", inline=True)
        embed.add_field(name="🌐 API", value=f"{self.bot.http_host}:{self.bot.http_port}", inline=True)
        embed.add_field(name="💾 Alerts", value=f"{self.bot.db.count_alerts()} total", inline=True)
        agents = self.bot.db.get_agents()
        online = sum(1 for a in agents if a.get("last_heartbeat"))
        embed.add_field(name="📱 Agents", value=f"{len(agents)} registered · {online} online", inline=True)
        embed.add_field(name="⚡ Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="📊 Servers", value=str(len(self.bot.guilds)), inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="summary", description="Threat summary")
    @app_commands.describe(hours="Hours to look back")
    async def summary(self, interaction: discord.Interaction, hours: int = 24):
        await interaction.response.defer()
        alerts = self.bot.db.get_alerts_recent(hours=hours)
        embed = discord.Embed(title=f"📊 Last {hours}h Summary", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        if not alerts:
            embed.description = "✅ No threats detected. All clear!"
            embed.color = discord.Color.green()
        else:
            sevs = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for a in alerts:
                s = a.get("severity", "MEDIUM")
                sevs[s] = sevs.get(s, 0) + 1
            embed.add_field(name="🔴 Critical", value=str(sevs["CRITICAL"]), inline=True)
            embed.add_field(name="🟠 High", value=str(sevs["HIGH"]), inline=True)
            embed.add_field(name="🟡 Medium", value=str(sevs["MEDIUM"]), inline=True)
            embed.add_field(name="🟢 Low", value=str(sevs["LOW"]), inline=True)
            embed.add_field(name="📊 Total", value=str(len(alerts)), inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
