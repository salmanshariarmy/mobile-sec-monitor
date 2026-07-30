import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import discord
from aiohttp import web

from config import Config


logger = logging.getLogger("http_api")

MAX_REQUEST_SIZE = 256 * 1024
ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class AlertAPI:
    def __init__(self, bot, db):
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
        """
        Authenticate an agent using its individual token.

        The shared HTTP_API_KEY is retained only as an optional
        migration fallback.
        """

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

        expected_token = agent_tokens.get(agent_id)

        if expected_token and hmac.compare_digest(
            supplied_token,
            expected_token,
        ):
            return True, agent_id

        legacy_key = str(
            getattr(Config, "HTTP_API_KEY", "")
        ).strip()

        allow_legacy = bool(
            getattr(Config, "ALLOW_LEGACY_API_KEY", False)
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
                "Agent %s authenticated using the legacy shared key.",
                agent_id,
            )
            return True, agent_id

        return False, agent_id

    async def _read_json(
        self,
        request: web.Request,
    ) -> Dict[str, Any]:
        """Read and validate a JSON object."""

        try:
            payload = await request.json()

        except Exception as error:
            raise web.HTTPBadRequest(
                text="Invalid JSON body."
            ) from error

        if not isinstance(payload, dict):
            raise web.HTTPBadRequest(
                text="JSON body must be an object."
            )

        return payload

    async def handle_alert(
        self,
        request: web.Request,
    ) -> web.Response:
        valid, agent_id = self._check_auth(request)

        if not valid:
            logger.warning(
                "Rejected unauthorized alert request for agent %r.",
                agent_id,
            )
            return web.json_response(
                {"error": "Unauthorized"},
                status=401,
            )

        try:
            payload = await self._read_json(request)
            payload = self._validate_alert(
                payload,
                agent_id,
            )

        except web.HTTPException:
            raise

        except ValueError as error:
            return web.json_response(
                {"error": str(error)},
                status=400,
            )

        try:
            alert_id = self.db.save_alert(payload)

        except Exception:
            logger.exception(
                "Failed to save alert from agent %s.",
                agent_id,
            )
            return web.json_response(
                {"error": "Unable to save alert"},
                status=500,
            )

        await self._send_discord_alert(payload)

        return web.json_response(
            {
                "status": "ok",
                "alert_id": alert_id,
            },
            status=201,
        )

    async def handle_heartbeat(
        self,
        request: web.Request,
    ) -> web.Response:
        valid, agent_id = self._check_auth(request)

        if not valid:
            return web.json_response(
                {"error": "Unauthorized"},
                status=401,
            )

        try:
            payload = await self._read_json(request)

        except web.HTTPBadRequest:
            return web.json_response(
                {"error": "Invalid JSON body"},
                status=400,
            )

        device_info = payload.get("device_info", {})

        if not isinstance(device_info, dict):
            return web.json_response(
                {
                    "error": (
                        "device_info must be a JSON object"
                    )
                },
                status=400,
            )

        try:
            self.db.register_agent(
                agent_id,
                device_info,
            )

        except Exception:
            logger.exception(
                "Failed to register heartbeat for agent %s.",
                agent_id,
            )
            return web.json_response(
                {"error": "Unable to register heartbeat"},
                status=500,
            )

        return web.json_response(
            {
                "status": "ok",
                "agent_id": agent_id,
            }
        )

    async def handle_commands(
        self,
        request: web.Request,
    ) -> web.Response:
        valid, agent_id = self._check_auth(request)

        if not valid:
            return web.json_response(
                {"error": "Unauthorized"},
                status=401,
            )

        try:
            commands = self.db.get_pending_commands(
                agent_id
            )

        except Exception:
            logger.exception(
                "Failed to retrieve commands for agent %s.",
                agent_id,
            )
            return web.json_response(
                {"error": "Unable to retrieve commands"},
                status=500,
            )

        return web.json_response(
            {"commands": commands or []}
        )

    async def handle_health(
        self,
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "status": "healthy",
                "service": "mobile-security-monitor",
            }
        )

    async def handle_root(
        self,
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "service": "Mobile Security Monitor",
                "version": "1.1.0",
            }
        )

    def _validate_alert(
        self,
        payload: Dict[str, Any],
        authenticated_agent_id: str,
    ) -> Dict[str, Any]:
        """
        Validate an alert and force the authenticated agent ID.

        This prevents an authenticated device from submitting an
        alert under another device's identity.
        """

        title = str(
            payload.get("title", "Security Alert")
        ).strip()

        description = str(
            payload.get("description", "")
        ).strip()

        severity = str(
            payload.get("severity", "MEDIUM")
        ).upper().strip()

        timestamp = str(
            payload.get("timestamp", "")
        ).strip()

        details = payload.get("details", {})
        device_info = payload.get("device_info", {})

        if not title:
            raise ValueError("Alert title cannot be empty.")

        if len(title) > 200:
            raise ValueError(
                "Alert title exceeds 200 characters."
            )

        if len(description) > 4000:
            raise ValueError(
                "Alert description exceeds 4000 characters."
            )

        if severity not in ALLOWED_SEVERITIES:
            raise ValueError(
                "Severity must be LOW, MEDIUM, HIGH, or CRITICAL."
            )

        if not isinstance(details, dict):
            raise ValueError(
                "Alert details must be a JSON object."
            )

        if not isinstance(device_info, dict):
            raise ValueError(
                "device_info must be a JSON object."
            )

        if not timestamp:
            timestamp = datetime.now(
                timezone.utc
            ).isoformat()

        return {
            "title": title,
            "description": description,
            "severity": severity,
            "timestamp": timestamp,
            "details": details,
            "agent_id": authenticated_agent_id,
            "device_info": device_info,
        }

    async def _send_discord_alert(
        self,
        payload: Dict[str, Any],
    ) -> None:
        channel_id = int(
            getattr(Config, "ALERT_CHANNEL_ID", 0)
        )

        if not channel_id:
            logger.warning(
                "ALERT_CHANNEL_ID is not configured."
            )
            return

        try:
            channel = self.bot.get_channel(channel_id)

            if channel is None:
                channel = await self.bot.fetch_channel(
                    channel_id
                )

            embed = self._build_embed(payload)
            await channel.send(embed=embed)

        except discord.Forbidden:
            logger.exception(
                "Discord bot lacks permission to send alerts."
            )

        except discord.NotFound:
            logger.exception(
                "Discord alert channel was not found."
            )

        except discord.HTTPException:
            logger.exception(
                "Discord rejected the alert message."
            )

        except Exception:
            logger.exception(
                "Unexpected error while sending Discord alert."
            )

    def _build_embed(
        self,
        alert: Dict[str, Any],
    ) -> discord.Embed:
        severity = str(
            alert.get("severity", "MEDIUM")
        ).upper()

        colors = {
            "CRITICAL": 0xFF0000,
            "HIGH": 0xFF6600,
            "MEDIUM": 0xFFAA00,
            "LOW": 0x00AA00,
        }

        emojis = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }

        embed = discord.Embed(
            title=(
                f"{emojis.get(severity, '⚪')} "
                f"{alert.get('title', 'Alert')}"
            ),
            description=str(
                alert.get("description", "")
            )[:4096],
            color=colors.get(
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
                alert.get("agent_id", "Unknown")
            )[:1024],
            inline=True,
        )

        embed.add_field(
            name="Time",
            value=str(
                alert.get("timestamp", "Unknown")
            )[:19],
            inline=True,
        )

        details = alert.get("details", {})

        if isinstance(details, dict):
            for key, value in list(
                details.items()
            )[:3]:
                embed.add_field(
                    name=str(key).replace(
                        "_",
                        " ",
                    ).title()[:256],
                    value=str(value)[:1024],
                    inline=True,
                )

        embed.set_footer(
            text="Mobile Security Monitor"
        )

        return embed

    async def start(self) -> None:
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(
            self.runner,
            self.bot.http_host,
            self.bot.http_port,
        )

        await site.start()

        logger.info(
            "HTTP API listening on %s:%s.",
            self.bot.http_host,
            self.bot.http_port,
        )

    async def stop(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None
