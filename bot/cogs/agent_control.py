import discord
from discord import app_commands
from discord.ext import commands

class AgentControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="agents", description="Control agents")
    @app_commands.describe(action="list, lockdown, resume", agent_id="Target agent ID")
    @app_commands.choices(action=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="lockdown", value="lockdown"),
        app_commands.Choice(name="resume", value="resume"),
    ])
    async def agents(self, interaction: discord.Interaction, action: str = "list", agent_id: str = None):
        await interaction.response.defer()
        if action == "list":
            agents = self.bot.db.get_agents()
            if not agents:
                await interaction.followup.send("📱 No agents registered.", ephemeral=True)
                return
            embed = discord.Embed(title="📱 Connected Agents", color=discord.Color.blue())
            for a in agents:
                status = "🟢 Online" if a.get("last_heartbeat") else "🔴 Offline"
                embed.add_field(name=f"{status} — {a.get('agent_id', '?')}",
                              value=f"Last HB: {a.get('last_heartbeat', 'never')}", inline=False)
            await interaction.followup.send(embed=embed)
        elif action == "lockdown":
            if not agent_id:
                await interaction.followup.send("❌ Specify agent_id", ephemeral=True)
                return
            self.bot.db.queue_command(agent_id, "lockdown")
            await interaction.followup.send(f"🔒 Lockdown queued for `{agent_id}`")
        elif action == "resume":
            if not agent_id:
                await interaction.followup.send("❌ Specify agent_id", ephemeral=True)
                return
            self.bot.db.queue_command(agent_id, "resume")
            await interaction.followup.send(f"✅ Resume queued for `{agent_id}`")

    @app_commands.command(name="block", description="Block a phone number")
    async def block(self, interaction: discord.Interaction, number: str):
        self.bot.db.add_blocked_number(number)
        await interaction.response.send_message(f"🚫 Blocked: `{number}`", ephemeral=True)

    @app_commands.command(name="whitelist", description="Whitelist a camera app")
    async def whitelist(self, interaction: discord.Interaction, package: str):
        self.bot.db.add_whitelisted_app(package)
        await interaction.response.send_message(f"✅ Whitelisted: `{package}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AgentControlCog(bot))
