"""
FastAPI HTTP server that receives alerts from Android agents.
Runs alongside the Discord bot.
"""
import asyncio
import datetime
import logging

from aiohttp import web
import discord

from ..config import Config

logger = logging.getLogger("http_api")


class AlertAPI:
    """HTTP handler for agent alerts."""

    def __init__(self, bot: discord.Client, db):
        self.bot = bot
        self.db = db
        self.app = web.Application()
        self.app.router.add_post("/alert", self.handle_alert)
        self.app.router.add_post("/agent/heartbeat", self.handle_heartbeat)
        self.app.router.add_get("/health", self.handle_health)

    async def _verify_auth(self, request) -> tuple[str, str] | None:
        """Verify agent authentication. Returns (agent_id, error_msg) or raises."""
        api_key = request.headers.get("X-API-Key", "")
        agent_id = request.headers.get("X-Agent-ID", "unknown")

        if not Config.is_agent_authorized(agent_id, api_key):
            return None, "Unauthorized — invalid API key or agent ID"
        return agent_id, None

    async def handle_alert(self, request):
        """Receive and process a security alert from an agent."""
        agent_id, err = await self._verify_auth(request)
        if err:
            return web.Response(status=403, text=err)

        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        alert = {
            "agent_id": agent_id or data.get("agent_id", "unknown"),
            "title": data.get("title", "Untitled Alert"),
            "description": data.get("description", ""),
            "severity": data.get("severity", "MEDIUM").upper(),
            "timestamp": data.get("timestamp", datetime.datetime.utcnow().isoformat()),
            "details": data.get("details", {}),
        }

        # Store in database
        self.db.insert_threat(**alert)

        # Update agent last-seen
        self.db.upsert_agent(alert["agent_id"], data.get("device_info"))

        # Send to Discord
        try:
            await self._send_discord_alert(alert)
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")

        logger.info(f"Alert received: [{alert['severity']}] {alert['title']} from {alert['agent_id']}")
        return web.Response(status=200, text="OK")

    async def handle_heartbeat(self, request):
        """Agent heartbeat / keep-alive."""
        agent_id, err = await self._verify_auth(request)
        if err:
            return web.Response(status=403, text=err)

        device_info = {}
        try:
            data = await request.json()
            device_info = data.get("device_info", {})
        except Exception:
            pass

        self.db.upsert_agent(agent_id or "unknown", device_info)
        return web.Response(status=200, text="OK")

    async def handle_health(self, request):
        return web.Response(status=200, text="OK")

    async def _send_discord_alert(self, alert: dict):
        """Build and send a Discord embed."""
        channel = self.bot.get_channel(Config.ALERT_CHANNEL_ID)
        if not channel:
            logger.warning(f"Alert channel {Config.ALERT_CHANNEL_ID} not found")
            return

        SEVERITY_COLORS = {
            "CRITICAL": 0xFF0000,
            "HIGH": 0xFF6600,
            "MEDIUM": 0xFFCC00,
            "LOW": 0x66CC66,
            "INFO": 0x3399FF,
        }

        sev = alert["severity"].upper()
        color = SEVERITY_COLORS.get(sev, 0x3399FF)
        ts = datetime.datetime.fromisoformat(alert["timestamp"])

        embed = discord.Embed(
            title=f"🚨 {alert['title']}",
            description=alert["description"],
            color=color,
            timestamp=ts,
        )
        for key, value in alert["details"].items():
            embed.add_field(
                name=key.replace("_", " ").title(),
                value=str(value)[:1024],
                inline=True
            )
        embed.set_footer(text=f"{sev} | Agent: {alert['agent_id']}")

        await channel.send(embed=embed)

        # Ping admin role for critical/high
        if sev in ("CRITICAL", "HIGH"):
            guild = channel.guild
            role = discord.utils.get(guild.roles, name=Config.ADMIN_ROLE_NAME)
            if role:
                await channel.send(f"{role.mention} — {alert['title']}")

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, Config.HTTP_HOST, Config.HTTP_PORT)
        await site.start()
        logger.info(f"HTTP API listening on {Config.HTTP_HOST}:{Config.HTTP_PORT}")
