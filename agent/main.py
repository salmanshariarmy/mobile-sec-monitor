#!/usr/bin/env python3
"""
Mobile Security Monitor — Android Agent Entry Point
Runs on Termux. Monitors camera, calls, SMS, network.
Pushes alerts to Discord bot via encrypted HTTP.
"""
import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
import threading
from typing import Callable

import requests

from config import AgentConfig
from monitors.camera_watcher import CameraWatcher
from monitors.call_monitor import CallMonitor
from monitors.sms_analyzer import SMSAnalyzer
from monitors.network_watch import NetworkWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent")


class SecurityAgent:
    """Main agent orchestrator."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.running = False
        self.monitors = []

    def send_alert(self, alert: dict):
        """Send alert to Discord bot via HTTP API."""
        payload = {
            "title": alert.get("title", "Unknown Alert"),
            "description": alert.get("description", ""),
            "severity": alert.get("severity", "MEDIUM").upper(),
            "timestamp": alert.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S")),
            "details": alert.get("details", {}),
            "agent_id": self.config.agent_id,
            "device_info": self.config.get_device_info(),
        }

        try:
            resp = requests.post(
                f"{self.config.bot_url}/alert",
                json=payload,
                headers={
                    "X-API-Key": self.config.api_key,
                    "X-Agent-ID": self.config.agent_id,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"✅ Alert sent: [{payload['severity']}] {payload['title']}")
            else:
                logger.warning(f"⚠️ Alert response {resp.status_code}: {resp.text[:100]}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Cannot reach bot at {self.config.bot_url}")
        except Exception as e:
            logger.error(f"❌ Alert send error: {e}")

    def send_heartbeat(self):
        """Send periodic heartbeat to bot."""
        while self.running:
            try:
                resp = requests.post(
                    f"{self.config.bot_url}/agent/heartbeat",
                    json={"device_info": self.config.get_device_info()},
                    headers={
                        "X-API-Key": self.config.api_key,
                        "X-Agent-ID": self.config.agent_id,
                    },
                    timeout=10,
                )
            except Exception:
                pass  # Heartbeat failures are non-critical
            time.sleep(60)  # Every 60 seconds

    def poll_commands(self):
        """Poll for pending commands from the bot."""
        # In production: query the bot's API endpoint for queued commands
        # For now, this is a stub for future implementation
        while self.running:
            time.sleep(30)

    def start(self):
        """Start all monitoring threads."""
        self.running = True
        logger.info(f"🚀 Starting Security Agent: {self.config.agent_id}")
        logger.info(f"📡 Bot URL: {self.config.bot_url}")

        # ── Monitors ──
        # Camera watcher (logcat-based, continuous)
        cam = CameraWatcher(self.send_alert, self.config)
        t_cam = threading.Thread(target=cam.run, daemon=True)
        t_cam.start()
        self.monitors.append(("Camera", t_cam))
        logger.info("📷 Camera watcher started")

        # Call monitor (periodic scan)
        call = CallMonitor(self.send_alert, self.config)
        t_call = threading.Thread(target=call.run, daemon=True)
        t_call.start()
        self.monitors.append(("Call", t_call))
        logger.info("📞 Call monitor started")

        # SMS analyzer (periodic scan)
        sms = SMSAnalyzer(self.send_alert, self.config)
        t_sms = threading.Thread(target=sms.run, daemon=True)
        t_sms.start()
        self.monitors.append(("SMS", t_sms))
        logger.info("💬 SMS analyzer started")

        # Network watch
        net = NetworkWatcher(self.send_alert, self.config)
        t_net = threading.Thread(target=net.run, daemon=True)
        t_net.start()
        self.monitors.append(("Network", t_net))
        logger.info("🌐 Network watcher started")

        # Heartbeat
        t_hb = threading.Thread(target=self.send_heartbeat, daemon=True)
        t_hb.start()

        # Command poller
        t_cmd = threading.Thread(target=self.poll_commands, daemon=True)
        t_cmd.start()

        logger.info(f"✅ All monitors active ({len(self.monitors)} threads)")

        # Keep alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested...")
            self.stop()

    def stop(self):
        self.running = False
        logger.info("Agent stopped.")


def main():
    parser = argparse.ArgumentParser(description="Mobile Security Agent")
    parser.add_argument("--bot-url", default=os.getenv("BOT_URL", "http://127.0.0.1:7879"),
                        help="Discord bot HTTP API URL")
    parser.add_argument("--api-key", default=os.getenv("API_KEY", ""),
                        help="API key for authentication")
    parser.add_argument("--agent-id", default=os.getenv("AGENT_ID", "android-001"),
                        help="Unique agent identifier")
    parser.add_argument("--scan-interval", type=int, default=30,
                        help="Call/SMS scan interval in seconds")
    args = parser.parse_args()

    config = AgentConfig(
        bot_url=args.bot_url.rstrip("/"),
        api_key=args.api_key,
        agent_id=args.agent_id,
        scan_interval=args.scan_interval,
    )

    agent = SecurityAgent(config)
    agent.start()


if __name__ == "__main__":
    main()
