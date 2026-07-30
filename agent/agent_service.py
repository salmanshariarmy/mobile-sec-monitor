"""
Mobile Security Monitor — Android background service entry point.
"""

import json
import logging
import os
import threading

from config import AgentConfig
from main_service import run_agent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("agent_service")

_stop_event = threading.Event()


def load_config() -> AgentConfig:
    """
    Load the agent configuration from agent_config.json.

    Falls back to development placeholders if the file is missing.
    Replace the placeholders before building the APK.
    """
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "agent_config.json",
    )

    default_config = {
        "bot_url": "https://your-server.com",
        "api_key": "replace-with-device-token",
        "agent_id": "android-apk-001",
        "scan_interval": 30,
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                values = json.load(file)

            default_config.update(values)

        except (OSError, json.JSONDecodeError) as error:
            logger.exception(
                "Unable to read agent_config.json: %s",
                error,
            )

    bot_url = str(default_config["bot_url"]).strip().rstrip("/")
    api_key = str(default_config["api_key"]).strip()
    agent_id = str(default_config["agent_id"]).strip()

    if not bot_url.startswith(("https://", "http://")):
        raise ValueError("bot_url must start with https:// or http://")

    if not api_key or api_key == "replace-with-device-token":
        raise ValueError(
            "A valid device API token must be configured."
        )

    if not agent_id:
        raise ValueError("agent_id cannot be empty.")

    return AgentConfig(
        bot_url=bot_url,
        api_key=api_key,
        agent_id=agent_id,
        scan_interval=max(
            10,
            int(default_config.get("scan_interval", 30)),
        ),
    )


def main() -> None:
    logger.info("Mobile Security Monitor service is starting.")

    try:
        config = load_config()

        logger.info(
            "Starting agent %s with a %s-second interval.",
            config.agent_id,
            config.scan_interval,
        )

        run_agent(
            config=config,
            stop_event=_stop_event,
        )

    except Exception:
        logger.exception("The monitoring service crashed.")

    finally:
        _stop_event.set()
        logger.info("Mobile Security Monitor service stopped.")


if __name__ == "__main__":
    main()
