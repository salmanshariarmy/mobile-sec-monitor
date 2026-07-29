"""
Central configuration — loaded from environment.
"""
import os
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Discord
    BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    GUILD_ID: int = int(os.getenv("GUILD_ID", "0"))
    ALERT_CHANNEL_ID: int = int(os.getenv("ALERT_CHANNEL_ID", "0"))
    ADMIN_ROLE_NAME: str = os.getenv("ADMIN_ROLE_NAME", "Security Admin")

    # HTTP API
    HTTP_HOST: str = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT: int = int(os.getenv("HTTP_PORT", "7879"))
    HTTP_API_KEY: str = os.getenv("HTTP_API_KEY", "")

    # DB
    DB_PATH: str = os.getenv("DB_PATH", "data/threats.db")

    # Agent auth tokens: dict[agent_id -> token]
    AGENT_AUTH_TOKENS: dict = {}
    _raw_tokens = os.getenv("AGENT_AUTH_TOKENS", "")
    if _raw_tokens:
        for pair in _raw_tokens.split(","):
            if ":" in pair:
                aid, tok = pair.split(":", 1)
                AGENT_AUTH_TOKENS[aid.strip()] = tok.strip()

    @classmethod
    def validate(cls):
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        if not cls.ALERT_CHANNEL_ID:
            errors.append("ALERT_CHANNEL_ID is required")
        if not cls.HTTP_API_KEY:
            errors.append("HTTP_API_KEY is required — set a random secret")
        if errors:
            raise ValueError("Config errors:\n" + "\n".join(errors))
        return True

    @classmethod
    def is_agent_authorized(cls, agent_id: str, token: str) -> bool:
        """Validate agent credentials."""
        expected = cls.AGENT_AUTH_TOKENS.get(agent_id)
        if expected and expected == token:
            return True
        # Fallback: if no per-agent tokens set, use the global API key
        return token == cls.HTTP_API_KEY
