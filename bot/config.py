import os
import json
from dotenv import load_dotenv

load_dotenv()


class Config:

    BOT_TOKEN: str = os.getenv(
        "DISCORD_BOT_TOKEN",
        ""
    )

    GUILD_ID: int = int(
        os.getenv("GUILD_ID", "0")
    )

    ALERT_CHANNEL_ID: int = int(
        os.getenv("ALERT_CHANNEL_ID", "0")
    )

    ADMIN_ROLE_NAME: str = os.getenv(
        "ADMIN_ROLE_NAME",
        "Security Admin"
    )

    HTTP_HOST: str = os.getenv(
        "HTTP_HOST",
        "0.0.0.0"
    )

    HTTP_PORT: int = int(
        os.getenv("HTTP_PORT", "7879")
    )

    HTTP_API_KEY: str = os.getenv(
        "HTTP_API_KEY",
        ""
    )

    DB_PATH: str = os.getenv(
        "DB_PATH",
        "data/threats.db"
    )


    AGENT_AUTH_TOKENS = json.loads(
        os.getenv(
            "AGENT_AUTH_TOKENS",
            "{}"
        )
    )


    @classmethod
    def validate(cls):

        errors = []

        if not cls.BOT_TOKEN:
            errors.append(
                "DISCORD_BOT_TOKEN is required"
            )

        if not cls.GUILD_ID:
            errors.append(
                "GUILD_ID is required"
            )

        if not cls.ALERT_CHANNEL_ID:
            errors.append(
                "ALERT_CHANNEL_ID is required"
            )

        if not cls.HTTP_API_KEY:
            errors.append(
                "HTTP_API_KEY is required"
            )

        if errors:
            raise ValueError(
                "Config errors:\n" +
                "\n".join(errors)
            )

        return True
