#!/usr/bin/env python3
"""
Mobile Security Monitor — Background Agent for APK.

Starts monitoring modules, sends alerts/heartbeats,
and shuts down cleanly using stop_event.
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

    if stop_event is None:
        stop_event = threading.Event()


    bot_url = str(
        config.bot_url
    ).rstrip("/")


    session = requests.Session()
    session.verify = True


    headers = {
        "X-API-Key": str(config.api_key),
        "X-Agent-ID": str(config.agent_id),
        "Content-Type": "application/json",
    }


    logger.info(
        "Starting security agent: %s",
        config.agent_id,
    )


    def get_device_info() -> Dict[str, Any]:

        try:

            method = getattr(
                config,
                "get_device_info",
                None,
            )


            if callable(method):

                result = method()

                if isinstance(result, dict):
                    return result


        except Exception:

            logger.exception(
                "Failed retrieving device information."
            )


        return {}



    def send_alert(
        alert: Dict[str, Any]
    ) -> None:


        if not isinstance(alert, dict):

            logger.warning(
                "Invalid alert ignored."
            )

            return



        severity = str(
            alert.get(
                "severity",
                "MEDIUM",
            )
        ).upper()



        if severity not in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }:

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
                    "Alert sent: %s",
                    payload["title"],
                )


            else:

                logger.warning(
                    "Alert failed %s",
                    response.status_code,
                )


        except requests.RequestException as error:

            logger.warning(
                "Alert connection failed: %s",
                error,
            )




    def send_heartbeat():

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
                        "Heartbeat failed: %s",
                        response.status_code,
                    )


            except requests.RequestException as error:

                logger.warning(
                    "Heartbeat error: %s",
                    error,
                )



            stop_event.wait(60)




    monitors = [

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



    for name, monitor_class in monitors:


        try:


            try:

                # New version
                monitor = monitor_class(
                    send_alert,
                    config,
                    stop_event,
                )


            except TypeError:

                # Backward compatibility
                logger.warning(
                    "%s does not support stop_event yet.",
                    name,
                )


                monitor = monitor_class(
                    send_alert,
                    config,
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
                "Failed starting %s monitor.",
                name,
            )




    heartbeat_thread = threading.Thread(
        target=send_heartbeat,
        name="Heartbeat",
        daemon=True,
    )


    heartbeat_thread.start()



    logger.info(
        "%d/%d monitors active.",
        len(monitor_threads),
        len(monitors),
    )



    try:

        while not stop_event.is_set():

            stop_event.wait(1)



    except KeyboardInterrupt:


        logger.info(
            "Keyboard interrupt."
        )

        stop_event.set()



    finally:


        logger.info(
            "Stopping monitors."
        )


        stop_event.set()



        for monitor in monitor_instances:


            stop = getattr(
                monitor,
                "stop",
                None,
            )


            if callable(stop):

                try:

                    stop()


                except Exception:

                    logger.exception(
                        "Monitor stop failed."
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
