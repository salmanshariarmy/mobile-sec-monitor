"""
Agent control commands — status, lockdown, scan, block.
"""
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json

from ..config import Config


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _forward_to_agent(self, agent_id: str, command: str, payload: dict = None):
        """
        Forward command to a specific agent.
        In production: this uses Firebase / WebSocket or a message queue.
        For now, we note it — the agent polls for commands.
        """
        # Store command in DB for agent to pick up
        db = self.bot.db
        details = {"command": command, "payload": payload or {}}
        db.insert_threat(
            agent_id=agent_id,
            title=f"AGENT_CMD:{command}",
            description=f"Command queued for {agent_id}",
            severity="INFO",
            details=details,
            timestamp=discord.utils.utcnow().isoformat()
        )
        return True

    @app_commands.command(name="agent", description="Control monitoring agents")
    @app_commands.describe(
        action="Action: status, lockdown, resume, scan",
        agent_id="Agent ID (default: all agents)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Check agent status", value="status"),
        app_commands.Choice(name="Lockdown device", value="lockdown"),
        app_commands.Choice(name="Resume monitoring", value="resume"),
        app_commands.Choice(name="Trigger scan", value="scan"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def agent(self, interaction: discord.Interaction,
                    action: str = "status",
                    agent_id: str = None):
        await interaction.response.defer()

        db = self.bot.db

        if action == "status":
            agents = db.get_agents()
            if not agents:
                return await interaction.followup.send("⚠️ No agents registered.")

            embed = discord.Embed(
                title="📡 Agent Status Dashboard",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            for a in agents:
                last_seen = a.get("last_seen", "never")
                status_emoji = "🟢" if a["status"] == "active" else "🔴"
                embed.add_field(
                    name=f"{status_emoji} {a['agent_id']}",
                    value=f"Last seen: {last_seen}\nStatus: {a['status']}",
                    inline=True
                )
            await interaction.followup.send(embed=embed)

        elif action in ("lockdown", "resume", "scan"):
            targets = [agent_id] if agent_id else [a["agent_id"] for a in db.get_agents()]
            if not targets:
                return await interaction.followup.send("⚠️ No agents found.")

            for aid in targets:
                await self._forward_to_agent(aid, action)

            await interaction.followup.send(
                f"✅ Command `{action}` sent to {len(targets)} agent(s): {', '.join(targets[:5])}"
                + ("..." if len(targets) > 5 else "")
            )

    @app_commands.command(name="block", description="Block a phone number or sender")
    @app_commands.describe(
        number="Phone number or sender to block",
        reason="Reason for blocking",
    )
    @app_commands.default_permissions(administrator=True)
    async def block(self, interaction: discord.Interaction,
                    number: str,
                    reason: str = "Security threat"):
        await interaction.response.defer()

        # Store in DB as a global blocklist entry
        db = self.bot.db
        db.insert_threat(
            agent_id="command",
            title=f"BLOCK:{number}",
            description=f"Block requested: {number} — {reason}",
            severity="HIGH",
            details={"number": number, "reason": reason, "requested_by": str(interaction.user)},
            timestamp=discord.utils.utcnow().isoformat()
        )

        embed = discord.Embed(
            title="⛔ Number Blocked",
            description=f"**{number}** has been added to the blocklist.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Requested by", value=interaction.user.mention)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="whitelist", description="Whitelist a trusted camera app")
    @app_commands.describe(
        package="Android package name (e.g. com.google.android.apps.camera)",
    )
    @app_commands.default_permissions(administrator=True)
    async def whitelist(self, interaction: discord.Interaction, package: str):
        db = self.bot.db
        db.insert_threat(
            agent_id="command",
            title=f"WHITELIST:{package}",
            description=f"App whitelisted for camera access",
            severity="INFO",
            details={"package": package, "requested_by": str(interaction.user)},
            timestamp=discord.utils.utcnow().isoformat()
        )
        await interaction.response.send_message(
            f"✅ **{package}** added to camera whitelist.", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
