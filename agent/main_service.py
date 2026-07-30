#!/usr/bin/env python3
"""
Mobile Security Monitor — Background Agent for APK.

Starts the monitoring components, sends alerts and heartbeats,
and shuts down cleanly when the service stop event is set.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

import requests

from monitors.camera_watcher import CameraWatcher
from monitors.call_monitor import CallMonitor
from monitors.sms_analyzer import SMSAnalyzer
from monitors.network_watch import NetworkWatcher


logger = logging.getLogger("main_service")


def run_agent(
    config: Any,
    stop_event: Optional[threading.Event] = None,
) -> None:
    """Run all security monitors in background threads."""

    if stop_event is None:
        stop_event = threading.Event()

    bot_url = str(config.bot_url).rstrip("/")
    session = requests.Session()

    headers = {
        "X-API-Key": str(config.api_key),
        "X-Agent-ID": str(config.agent_id),
        "Content-Type": "application/json",
    }

    logger.info(
        "Security agent %s is starting.",
        config.agent_id,
    )

    def get_device_info() -> Dict[str, Any]:
        """Safely retrieve device information from the configuration."""

        get_info = getattr(config, "get_device_info", None)

        if not callable(get_info):
            return {}

        try:
            device_info = get_info()
            return device_info if isinstance(device_info, dict) else {}

        except Exception:
            logger.exception("Unable to retrieve device information.")
            return {}

    def send_alert(alert: Dict[str, Any]) -> None:
        """Send a security alert to the server."""

        if not isinstance(alert, dict):
            logger.warning("Ignored invalid alert object: %r", alert)
            return

        severity = str(
            alert.get("severity", "MEDIUM")
        ).upper()

        allowed_severities = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }

        if severity not in allowed_severities:
            severity = "MEDIUM"

        details = alert.get("details", {})

        if not isinstance(details, dict):
            details = {"value": str(details)}

        payload = {
            "title": str(
                alert.get("title", "Security Alert")
            )[:200],
            "description": str(
                alert.get("description", "")
            )[:4000],
            "severity": severity,
            "timestamp": str(
                alert.get(
                    "timestamp",
                    time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(),
                    ),
                )
            ),
            "details": details,
            "agent_id": str(config.agent_id),
            "device_info": get_device_info(),
        }

        try:
            response = session.post(
                f"{bot_url}/alert",
                json=payload,
                headers=headers,
                timeout=10,
            )

            if response.status_code in (200, 201, 202):
                logger.info(
                    "Alert sent: [%s] %s",
                    payload["severity"],
                    payload["title"],
                )
            else:
                logger.warning(
                    "Alert request failed with status %s: %s",
                    response.status_code,
                    response.text[:500],
                )

        except requests.RequestException as error:
            logger.warning(
                "Unable to send alert to the server: %s",
                error,
            )

    def send_heartbeat() -> None:
        """Send periodic heartbeats until shutdown is requested."""

        while not stop_event.is_set():
            payload = {
                "agent_id": str(config.agent_id),
                "device_info": get_device_info(),
                "timestamp": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(),
                ),
            }

            try:
                response = session.post(
                    f"{bot_url}/agent/heartbeat",
                    json=payload,
                    headers=headers,
                    timeout=10,
                )

                if response.status_code not in (200, 201, 202):
                    logger.warning(
                        "Heartbeat failed with status %s: %s",
                        response.status_code,
                        response.text[:500],
                    )

            except requests.RequestException as error:
                logger.warning(
                    "Unable to send heartbeat: %s",
                    error,
                )

            # Wait for 60 seconds, but stop immediately if requested.
            stop_event.wait(60)

    monitor_definitions = [
        ("Camera", CameraWatcher),
        ("Call", CallMonitor),
        ("SMS", SMSAnalyzer),
        ("Network", NetworkWatcher),
    ]

    monitor_instances = []
    monitor_threads = []

    for name, monitor_class in monitor_definitions:
        try:
            monitor = monitor_class(send_alert, config)
            monitor_instances.append(monitor)

            thread = threading.Thread(
                target=monitor.run,
                name=f"{name}Monitor",
                daemon=True,
            )
            thread.start()
            monitor_threads.append(thread)

            logger.info("%s monitor started.", name)

        except Exception:
            logger.exception(
                "Unable to start the %s monitor.",
                name,
            )

    heartbeat_thread = threading.Thread(
        target=send_heartbeat,
        name="Heartbeat",
        daemon=True,
    )
    heartbeat_thread.start()

    logger.info(
        "%s of %s monitors are active.",
        len(monitor_threads),
        len(monitor_definitions),
    )

    try:
        while not stop_event.is_set():
            stop_event.wait(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interruption received.")
        stop_event.set()

    finally:
        logger.info("Stopping security monitors.")

        for monitor in monitor_instances:
            stop_method = getattr(monitor, "stop", None)

            if callable(stop_method):
                try:
                    stop_method()
                except Exception:
                    logger.exception(
                        "A monitor failed during shutdown."
                    )

        stop_event.set()
        session.close()

        logger.info("Security agent stopped.")
