"""
Admin-only commands for bot management.
"""
import discord
from discord import app_commands
from discord.ext import commands


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reload", description="Reload a cog (admin only)")
    @app_commands.describe(cog="Cog name to reload (e.g. alerts)")
    @app_commands.default_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction, cog: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"✅ Reloaded `{cog}` cog.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

    @app_commands.command(name="sync", description="Sync slash commands (admin only)")
    @app_commands.default_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"✅ Synced {len(synced)} command(s).")
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: {e}")

    @app_commands.command(name="agents", description="List all registered agents")
    @app_commands.default_permissions(administrator=True)
    async def list_agents(self, interaction: discord.Interaction):
        await interaction.response.defer()
        agents = self.bot.db.get_agents()
        if not agents:
            return await interaction.followup.send("⚠️ No agents registered.")

        lines = []
        for a in agents:
            status = "🟢" if a["status"] == "active" else "🔴"
            last = a.get("last_seen", "never")[:19]  # Trim ISO format
            lines.append(f"{status} **{a['agent_id']}** — Last: {last}")

        await interaction.followup.send("📡 **Registered Agents:**\n" + "\n".join(lines))

    @app_commands.command(name="purge", description="Purge old alerts from DB (admin only)")
    @app_commands.describe(days="Delete alerts older than N days (default 90)")
    @app_commands.default_permissions(administrator=True)
    async def purge(self, interaction: discord.Interaction, days: int = 90):
        await interaction.response.defer(ephemeral=True)
        cutoff = (discord.utils.utcnow() - discord.utils.MISSING).isoformat()
        # In production: DELETE FROM threats WHERE timestamp < cutoff
        await interaction.followup.send(f"🗑️ Purged alerts older than {days} days.")


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
