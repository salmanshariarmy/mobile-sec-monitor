#!/usr/bin/env python3
"""
Mobile Security Monitor — Background Agent for APK
This runs as a daemon thread inside the APK's foreground service.
"""
import time
import logging
import threading

from monitors.camera_watcher import CameraWatcher
from monitors.call_monitor import CallMonitor
from monitors.sms_analyzer import SMSAnalyzer
from monitors.network_watch import NetworkWatcher

logger = logging.getLogger("agent_service")


def run_agent(config):
    """Run all monitors in background threads."""
    logger.info("🚀 Security Agent starting in background")

    def send_alert(alert):
        """Send alert to Discord bot via HTTP."""
        import requests
        import json
        import time as t

        payload = {
            "title": alert.get("title", "Alert"),
            "description": alert.get("description", ""),
            "severity": alert.get("severity", "MEDIUM").upper(),
            "timestamp": alert.get("timestamp", t.strftime("%Y-%m-%dT%H:%M:%S")),
            "details": alert.get("details", {}),
            "agent_id": config.agent_id,
            "device_info": config.get_device_info(),
        }

        try:
            resp = requests.post(
                f"{config.bot_url}/alert",
                json=payload,
                headers={
                    "X-API-Key": config.api_key,
                    "X-Agent-ID": config.agent_id,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info(f"✅ Alert sent: [{payload['severity']}] {payload['title']}")
            else:
                logger.warning(f"⚠️ Alert response {resp.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Cannot reach bot: {e}")

    def send_heartbeat():
        """Periodic heartbeat."""
        import requests
        while True:
            try:
                requests.post(
                    f"{config.bot_url}/agent/heartbeat",
                    json={"device_info": config.get_device_info()},
                    headers={
                        "X-API-Key": config.api_key,
                        "X-Agent-ID": config.agent_id,
                    },
                    timeout=10,
                )
            except:
                pass
            time.sleep(60)

    # Start monitors
    monitors = [
        ("Camera", CameraWatcher(send_alert, config)),
        ("Call", CallMonitor(send_alert, config)),
        ("SMS", SMSAnalyzer(send_alert, config)),
        ("Network", NetworkWatcher(send_alert, config)),
    ]

    threads = []
    for name, monitor in monitors:
        t = threading.Thread(target=monitor.run, daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"📷 {name} monitor started")

    # Heartbeat
    t_hb = threading.Thread(target=send_heartbeat, daemon=True)
    t_hb.start()

    logger.info(f"✅ All monitors active ({len(threads)} threads)")

    # Keep alive
    while True:
        time.sleep(1)
