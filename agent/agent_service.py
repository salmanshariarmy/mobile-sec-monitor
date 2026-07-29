"""
Mobile Security Monitor — Android Foreground Service
"""
import os
import threading
import logging

from jnius import autoclass
from main import SecurityAgent
from config import AgentConfig

# Android classes
PythonActivity = autoclass('org.kivy.android.PythonActivity')
Service = autoclass('org.kivy.android.service.BasicService')
Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')

logger = logging.getLogger("agent_service")

class MonitorService(Service):
    """Android foreground service that keeps the agent alive."""

    def onCreate(self):
        super().onCreate()
        logger.info("MonitorService created")
        self.agent = None

    def onStartCommand(self, intent, flags, startId):
        logger.info("MonitorService start command received")
        if self.agent is None:
            t = threading.Thread(target=self._start_agent, daemon=True)
            t.start()
        return Service.START_STICKY

    def _start_agent(self):
        try:
            # Read config from a small file on the device
            config_path = os.path.join(
                os.path.dirname(__file__), "agent_config.json"
            )
            if os.path.exists(config_path):
                import json
                with open(config_path) as f:
                    cfg = json.load(f)
            else:
                # Hardcoded defaults (change before building)
                cfg = {
                    "bot_url": "https://your-server.com",
                    "api_key": "your-api-key",
                    "agent_id": "android-apk-001",
                    "scan_interval": 30
                }

            config = AgentConfig(
                bot_url=cfg["bot_url"],
                api_key=cfg["api_key"],
                agent_id=cfg["agent_id"],
                scan_interval=int(cfg.get("scan_interval", 30)),
            )
            self.agent = SecurityAgent(config)
            self.agent.start()
        except Exception as e:
            logger.error(f"Agent crashed: {e}")

    def onDestroy(self):
        logger.info("MonitorService destroyed")
        if self.agent:
            self.agent.stop()
        super().onDestroy()
