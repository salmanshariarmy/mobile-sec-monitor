import discord
from discord import app_commands
from discord.ext import commands

class DashboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dashboard", description="Interactive threat dashboard")
    async def dashboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(title="🛡️ Security Monitor — Dashboard", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        total = self.bot.db.count_alerts()
        recent = self.bot.db.get_alerts_recent(hours=24)
        agents = self.bot.db.get_agents()
        embed.add_field(name="📊 Total Alerts", value=str(total), inline=True)
        embed.add_field(name="📈 Last 24h", value=str(len(recent)), inline=True)
        embed.add_field(name="📱 Agents", value=str(len(agents)), inline=True)
        if recent:
            crit = sum(1 for a in recent if a.get("severity") == "CRITICAL")
            high = sum(1 for a in recent if a.get("severity") == "HIGH")
            med = sum(1 for a in recent if a.get("severity") == "MEDIUM")
            low = sum(1 for a in recent if a.get("severity") == "LOW")
            embed.add_field(name="Severity (24h)", value=f"🔴 {crit} 🟠 {high} 🟡 {med} 🟢 {low}", inline=False)
        view = DashboardView(self.bot)
        await interaction.followup.send(embed=embed, view=view)

class DashboardView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Last 10", style=discord.ButtonStyle.primary, emoji="📋")
    async def last_ten(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        alerts = self.bot.db.get_alerts(limit=10)
        if not alerts:
            await interaction.followup.send("No alerts.", ephemeral=True)
            return
        text = "\n".join(f"[{a.get('severity','?')}] {a.get('title','?')}" for a in alerts)
        await interaction.followup.send(f"**Last 10 Alerts:**\n{text}", ephemeral=True)

    @discord.ui.button(label="Agents", style=discord.ButtonStyle.success, emoji="📱")
    async def agents_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        agents = self.bot.db.get_agents()
        text = "\n".join(f"{'🟢' if a.get('last_heartbeat') else '🔴'} {a.get('agent_id','?')}" for a in agents) or "None"
        await interaction.followup.send(f"**Agents:**\n{text}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DashboardCog(bot))
