import json, logging, time
from aiohttp import web

logger = logging.getLogger("http_api")

class AlertAPI:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.app = web.Application()
        self.runner = None
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_post("/alert", self.handle_alert)
        self.app.router.add_post("/agent/heartbeat", self.handle_heartbeat)
        self.app.router.add_get("/agent/commands", self.handle_commands)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/", self.handle_root)

    def _check_auth(self, request):
        api_key = request.headers.get("X-API-Key", "")
        from config import Config
        return api_key == Config.HTTP_API_KEY, request.headers.get("X-Agent-ID", "unknown")

    async def handle_alert(self, request):
        try:
            payload = await request.json()
        except:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        valid, agent_id = self._check_auth(request)
        if not valid:
            return web.json_response({"error": "Unauthorized"}, status=401)
        alert_id = self.db.save_alert(payload)
        try:
            channel = self.bot.get_channel(int(os.getenv("ALERT_CHANNEL_ID", "0")))
            if channel:
                embed = self._build_embed(payload)
                await channel.send(embed=embed)
        except:
            pass
        return web.json_response({"status": "ok", "alert_id": alert_id})

    async def handle_heartbeat(self, request):
        try:
            payload = await request.json()
        except:
            payload = {}
        valid, agent_id = self._check_auth(request)
        if not valid:
            return web.json_response({"error": "Unauthorized"}, status=401)
        self.db.register_agent(agent_id, payload.get("device_info"))
        return web.json_response({"status": "ok"})

    async def handle_commands(self, request):
        valid, agent_id = self._check_auth(request)
        if not valid:
            return web.json_response({"error": "Unauthorized"}, status=401)
        cmds = self.db.get_pending_commands(agent_id)
        return web.json_response({"commands": cmds})

    async def handle_health(self, request):
        return web.json_response({"status": "healthy", "alerts": self.db.count_alerts()})

    async def handle_root(self, request):
        return web.json_response({"service": "Mobile Security Monitor", "version": "1.0.0"})

    def _build_embed(self, alert):
        sev = alert.get("severity", "MEDIUM").upper()
        colors = {"CRITICAL": 0xFF0000, "HIGH": 0xFF6600, "MEDIUM": 0xFFAA00, "LOW": 0x00FF00}
        emojis = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
        embed = {
            "title": f"{emojis.get(sev,'⚪')} {alert.get('title','Alert')}",
            "description": alert.get("description", ""),
            "color": colors.get(sev, 0x3498DB),
            "fields": [
                {"name": "Severity", "value": sev, "inline": True},
                {"name": "Agent", "value": alert.get("agent_id","?"), "inline": True},
                {"name": "Time", "value": alert.get("timestamp","")[:19], "inline": True}
            ],
            "footer": {"text": "Mobile Security Monitor"},
            "timestamp": alert.get("timestamp", "")
        }
        details = alert.get("details", {})
        if isinstance(details, dict):
            for k, v in list(details.items())[:3]:
                embed["fields"].append({"name": k.capitalize(), "value": str(v)[:200], "inline": True})
        return embed

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.bot.http_host, self.bot.http_port)
        await site.start()
        logger.info(f"🌐 HTTP API on {self.bot.http_host}:{self.bot.http_port}")

    async def stop(self):
        if self.runner: await self.runner.cleanup()
