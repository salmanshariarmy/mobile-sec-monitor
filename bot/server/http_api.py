import hmac
import io
import logging

from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import discord
from aiohttp import web

from config import Config


logger = logging.getLogger("http_api")


MAX_REQUEST_SIZE = 10 * 1024 * 1024  # allow image upload
ALLOWED_SEVERITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


class AlertAPI:

    def __init__(
        self,
        bot,
        db,
    ):

        self.bot = bot
        self.db = db

        self.app = web.Application(
            client_max_size=MAX_REQUEST_SIZE
        )

        self.runner = None

        self._setup_routes()



    def _setup_routes(self):

        self.app.router.add_post(
            "/alert",
            self.handle_alert,
        )

        self.app.router.add_post(
            "/alert/image",
            self.handle_alert_image,
        )

        self.app.router.add_post(
            "/agent/heartbeat",
            self.handle_heartbeat,
        )

        self.app.router.add_get(
            "/agent/commands",
            self.handle_commands,
        )

        self.app.router.add_get(
            "/health",
            self.handle_health,
        )

        self.app.router.add_get(
            "/",
            self.handle_root,
        )



    def _check_auth(
        self,
        request: web.Request,
    ) -> Tuple[bool, str]:


        agent_id = request.headers.get(
            "X-Agent-ID",
            "",
        ).strip()


        supplied_token = request.headers.get(
            "X-API-Key",
            "",
        ).strip()



        if not agent_id or not supplied_token:

            return False, ""



        agent_tokens = getattr(
            Config,
            "AGENT_AUTH_TOKENS",
            {},
        )



        expected_token = agent_tokens.get(
            agent_id
        )



        if expected_token and hmac.compare_digest(
            supplied_token,
            expected_token,
        ):

            return True, agent_id



        legacy_key = str(
            getattr(
                Config,
                "HTTP_API_KEY",
                "",
            )
        ).strip()



        allow_legacy = bool(
            getattr(
                Config,
                "ALLOW_LEGACY_API_KEY",
                False,
            )
        )



        if (
            allow_legacy
            and legacy_key
            and hmac.compare_digest(
                supplied_token,
                legacy_key,
            )
        ):

            logger.warning(
                "Agent %s using legacy key",
                agent_id,
            )

            return True, agent_id



        return False, agent_id



    async def _read_json(
        self,
        request: web.Request,
    ) -> Dict[str, Any]:


        try:

            payload = await request.json()


        except Exception as error:

            raise web.HTTPBadRequest(
                text="Invalid JSON body"
            ) from error



        if not isinstance(
            payload,
            dict,
        ):

            raise web.HTTPBadRequest(
                text="JSON must be object"
            )



        return payload



    async def handle_alert(
        self,
        request: web.Request,
    ) -> web.Response:


        valid, agent_id = self._check_auth(
            request
        )


        if not valid:

            return web.json_response(
                {
                    "error":
                    "Unauthorized"
                },
                status=401,
            )



        payload = await self._read_json(
            request
        )


        payload = self._validate_alert(
            payload,
            agent_id,
        )



        alert_id = self.db.save_alert(
            payload
        )


        await self._send_discord_alert(
            payload
        )



        return web.json_response(
            {
                "status":
                "ok",

                "alert_id":
                alert_id,
            },
            status=201,
        )



    async def handle_alert_image(
        self,
        request: web.Request,
    ) -> web.Response:


        valid, agent_id = self._check_auth(
            request
        )


        if not valid:

            return web.json_response(
                {
                    "error":
                    "Unauthorized"
                },
                status=401,
            )



        reader = await request.multipart()


        title = "📷 Camera Alert"
        description = ""
        severity = "HIGH"

        image_data = None



        async for part in reader:


            if part.name == "image":

                image_data = await part.read()



            elif part.name == "title":

                title = await part.text()



            elif part.name == "description":

                description = await part.text()



            elif part.name == "severity":

                severity = await part.text()



        payload = {

            "title":
            title,


            "description":
            description,


            "severity":
            severity.upper(),


            "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),


            "details":
            {
                "source":
                "camera_monitor"
            },


            "agent_id":
            agent_id,


            "device_info":
            {}

        }



        alert_id = self.db.save_alert(
            payload
        )


        await self._send_discord_image(
            payload,
            image_data,
        )



        return web.json_response(
            {
                "status":
                "ok",

                "alert_id":
                alert_id,
            },
            status=201,
        )
            async def handle_heartbeat(
        self,
        request: web.Request,
    ) -> web.Response:


        valid, agent_id = self._check_auth(
            request
        )


        if not valid:

            return web.json_response(
                {
                    "error":
                    "Unauthorized"
                },
                status=401,
            )



        try:

            payload = await self._read_json(
                request
            )


        except web.HTTPBadRequest:

            return web.json_response(
                {
                    "error":
                    "Invalid JSON body"
                },
                status=400,
            )



        device_info = payload.get(
            "device_info",
            {},
        )



        if not isinstance(
            device_info,
            dict,
        ):

            return web.json_response(
                {
                    "error":
                    "device_info must be object"
                },
                status=400,
            )



        self.db.register_agent(
            agent_id,
            device_info,
        )



        return web.json_response(
            {
                "status":
                "ok",

                "agent_id":
                agent_id,
            }
        )



    async def handle_commands(
        self,
        request: web.Request,
    ) -> web.Response:


        valid, agent_id = self._check_auth(
            request
        )


        if not valid:

            return web.json_response(
                {
                    "error":
                    "Unauthorized"
                },
                status=401,
            )



        commands = self.db.get_pending_commands(
            agent_id
        )


        return web.json_response(
            {
                "commands":
                commands or []
            }
        )



    async def handle_health(
        self,
        request: web.Request,
    ) -> web.Response:


        return web.json_response(
            {
                "status":
                "healthy",

                "service":
                "mobile-security-monitor",
            }
        )



    async def handle_root(
        self,
        request: web.Request,
    ) -> web.Response:


        return web.json_response(
            {
                "service":
                "Mobile Security Monitor",

                "version":
                "1.2.0",
            }
        )



    def _validate_alert(
        self,
        payload: Dict[str, Any],
        authenticated_agent_id: str,
    ) -> Dict[str, Any]:


        title = str(
            payload.get(
                "title",
                "Security Alert",
            )
        ).strip()



        description = str(
            payload.get(
                "description",
                "",
            )
        ).strip()



        severity = str(
            payload.get(
                "severity",
                "MEDIUM",
            )
        ).upper().strip()



        timestamp = str(
            payload.get(
                "timestamp",
                "",
            )
        ).strip()



        details = payload.get(
            "details",
            {},
        )



        device_info = payload.get(
            "device_info",
            {},
        )



        if severity not in ALLOWED_SEVERITIES:

            raise ValueError(
                "Invalid severity"
            )



        if not isinstance(
            details,
            dict,
        ):

            raise ValueError(
                "details must be object"
            )



        if not isinstance(
            device_info,
            dict,
        ):

            raise ValueError(
                "device_info must be object"
            )



        if not timestamp:

            timestamp = datetime.now(
                timezone.utc
            ).isoformat()



        return {

            "title":
            title,


            "description":
            description,


            "severity":
            severity,


            "timestamp":
            timestamp,


            "details":
            details,


            "agent_id":
            authenticated_agent_id,


            "device_info":
            device_info,
        }




    async def _send_discord_alert(
        self,
        payload,
    ):


        channel_id = int(
            getattr(
                Config,
                "ALERT_CHANNEL_ID",
                0,
            )
        )


        if not channel_id:

            return



        channel = self.bot.get_channel(
            channel_id
        )


        if channel is None:

            channel = await self.bot.fetch_channel(
                channel_id
            )



        embed = self._build_embed(
            payload
        )


        await channel.send(
            embed=embed
        )



    async def _send_discord_image(
        self,
        payload,
        image_data,
    ):


        channel_id = int(
            getattr(
                Config,
                "ALERT_CHANNEL_ID",
                0,
            )
        )


        if not channel_id:

            logger.warning(
                "Missing ALERT_CHANNEL_ID"
            )

            return



        channel = self.bot.get_channel(
            channel_id
        )



        if channel is None:

            channel = await self.bot.fetch_channel(
                channel_id
            )



        embed = self._build_embed(
            payload
        )



        if image_data:


            file = discord.File(
                io.BytesIO(image_data),
                filename="camera.jpg",
            )


            await channel.send(
                embed=embed,
                file=file,
            )


        else:

            await channel.send(
                embed=embed
            )




    def _build_embed(
        self,
        alert,
    ):


        severity = str(
            alert.get(
                "severity",
                "MEDIUM",
            )
        ).upper()



        colors = {

            "CRITICAL":
            0xFF0000,

            "HIGH":
            0xFF6600,

            "MEDIUM":
            0xFFAA00,

            "LOW":
            0x00AA00,
        }



        emojis = {

            "CRITICAL":
            "🔴",

            "HIGH":
            "🟠",

            "MEDIUM":
            "🟡",

            "LOW":
            "🟢",
        }



        embed = discord.Embed(

            title=
            f"{emojis.get(severity,'⚪')} "
            f"{alert.get('title','Alert')}",


            description=
            alert.get(
                "description",
                "",
            )[:4096],


            color=
            colors.get(
                severity,
                0x3498DB,
            ),
        )



        embed.add_field(
            name="Severity",
            value=severity,
            inline=True,
        )


        embed.add_field(
            name="Agent",
            value=str(
                alert.get(
                    "agent_id",
                    "Unknown",
                )
            ),
            inline=True,
        )


        embed.add_field(
            name="Time",
            value=str(
                alert.get(
                    "timestamp",
                    "",
                )
            )[:19],
            inline=True,
        )



        details = alert.get(
            "details",
            {},
        )


        if isinstance(
            details,
            dict,
        ):

            for key, value in list(
                details.items()
            )[:3]:

                embed.add_field(
                    name=str(key).title(),
                    value=str(value)[:1024],
                    inline=True,
                )



        embed.set_footer(
            text="Mobile Security Monitor"
        )


        return embed




    async def start(
        self,
    ):


        self.runner = web.AppRunner(
            self.app
        )


        await self.runner.setup()



        site = web.TCPSite(
            self.runner,
            self.bot.http_host,
            self.bot.http_port,
        )



        await site.start()



        logger.info(
            "HTTP API running %s:%s",
            self.bot.http_host,
            self.bot.http_port,
        )




    async def stop(
        self,
    ):


        if self.runner:

            await self.runner.cleanup()

            self.runner = None
