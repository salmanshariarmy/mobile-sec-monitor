#!/usr/bin/env python3
"""
Mobile Security Monitor — Background Agent for APK.

Starts the monitoring components, sends alerts and heartbeats,
and shuts down cleanly when the stop event is triggered.
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
    """
    Start all security monitoring components.
    """

    if stop_event is None:
        stop_event = threading.Event()

    bot_url = str(config.bot_url).rstrip("/")

    session = requests.Session()
    session.verify = True

    headers = {
        "X-API-Key": str(config.api_key),
        "X-Agent-ID": str(config.agent_id),
        "Content-Type": "application/json",
    }

    logger.info(
        "Security agent %s starting.",
        config.agent_id,
    )


    def get_device_info() -> Dict[str, Any]:
        """
        Safely retrieve device information.
        """

        get_info = getattr(
            config,
            "get_device_info",
            None,
        )

        if not callable(get_info):
            return {}

        try:
            info = get_info()

            if isinstance(info, dict):
                return info

            return {}

        except Exception:
            logger.exception(
                "Unable to get device information."
            )

            return {}


    def send_alert(
        alert: Dict[str, Any],
    ) -> None:
        """
        Send alert to server.
        """

        if not isinstance(alert, dict):
            logger.warning(
                "Invalid alert ignored: %s",
                alert,
            )
            return


        severity = str(
            alert.get(
                "severity",
                "MEDIUM",
            )
        ).upper()


        allowed_severity = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }


        if severity not in allowed_severity:
            severity = "MEDIUM"


        details = alert.get(
            "details",
            {},
        )


        if not isinstance(details, dict):
            details = {
                "value": str(details)
            }


        payload = {
            "title": str(
                alert.get(
                    "title",
                    "Security Alert",
                )
            )[:200],

            "description": str(
                alert.get(
                    "description",
                    "",
                )
            )[:4000],

            "severity": severity,

            "timestamp": alert.get(
                "timestamp",
                time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(),
                ),
            ),

            "details": details,

            # Server will enforce authenticated agent ID
            "device_info": get_device_info(),
        }


        try:
            response = session.post(
                f"{bot_url}/alert",
                json=payload,
                headers=headers,
                timeout=10,
            )


            if response.status_code in (
                200,
                201,
                202,
            ):

                logger.info(
                    "Alert sent [%s] %s",
                    severity,
                    payload["title"],
                )

            else:

                logger.warning(
                    "Alert failed %s: %s",
                    response.status_code,
                    response.text[:300],
                )


        except requests.RequestException as error:

            logger.warning(
                "Alert connection failed: %s",
                error,
            )



    def send_heartbeat() -> None:
        """
        Send heartbeat every 60 seconds.
        """

        while not stop_event.is_set():

            payload = {
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


                if response.status_code not in (
                    200,
                    201,
                    202,
                ):

                    logger.warning(
                        "Heartbeat failed %s: %s",
                        response.status_code,
                        response.text[:300],
                    )


            except requests.RequestException as error:

                logger.warning(
                    "Heartbeat connection failed: %s",
                    error,
                )


            # Wait but allow immediate shutdown
            stop_event.wait(60)



    monitor_definitions = [

        (
            "Camera",
            CameraWatcher,
        ),

        (
            "Call",
            CallMonitor,
        ),

        (
            "SMS",
            SMSAnalyzer,
        ),

        (
            "Network",
            NetworkWatcher,
        ),

    ]


    monitor_instances = []

    monitor_threads = []


    for name, monitor_class in monitor_definitions:

        try:

            monitor = monitor_class(
                send_alert,
                config,
                stop_event,
            )


            monitor_instances.append(
                monitor
            )


            thread = threading.Thread(
                target=monitor.run,
                name=f"{name}Monitor",
                daemon=True,
            )


            thread.start()


            monitor_threads.append(
                thread
            )


            logger.info(
                "%s monitor started.",
                name,
            )


        except Exception:

            logger.exception(
                "Unable to start %s monitor.",
                name,
            )



    heartbeat_thread = threading.Thread(
        target=send_heartbeat,
        name="Heartbeat",
        daemon=True,
    )


    heartbeat_thread.start()



    logger.info(
        "%s/%s monitors active.",
        len(monitor_threads),
        len(monitor_definitions),
    )



    try:

        while not stop_event.is_set():

            stop_event.wait(1)



    except KeyboardInterrupt:

        logger.info(
            "Keyboard interrupt received."
        )

        stop_event.set()



    finally:

        logger.info(
            "Stopping security monitors."
        )


        stop_event.set()



        for monitor in monitor_instances:

            stop_method = getattr(
                monitor,
                "stop",
                None,
            )


            if callable(stop_method):

                try:

                    stop_method()


                except Exception:

                    logger.exception(
                        "Monitor shutdown failed."
                    )



        for thread in monitor_threads:

            thread.join(
                timeout=5
            )



        if heartbeat_thread.is_alive():

            heartbeat_thread.join(
                timeout=5
            )



        session.close()


        logger.info(
            "Security agent stopped."
        )
