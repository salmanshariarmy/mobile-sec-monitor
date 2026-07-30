import subprocess
import os
import time
import logging
from datetime import datetime

logger = logging.getLogger("camera_watcher")


def take_photo_and_send(config, alert_callback):
    """Capture a photo via Android camera intent and upload to server."""
    try:
        import requests

        filename = "/sdcard/DCIM/security_alert.jpg"

        # Launch Android camera capture intent
        subprocess.run(
            [
                "sh",
                "-c",
                f"am start -a android.media.action.IMAGE_CAPTURE --output {filename}"
            ],
            timeout=5
        )

        # Give the camera time to capture and save
        time.sleep(3)

        if not os.path.exists(filename):
            logger.warning("Photo file not found at %s", filename)
            return

        with open(filename, "rb") as image:
            response = requests.post(
                f"{config.bot_url}/alert/image",
                files={
                    "image": (
                        "camera.jpg",
                        image,
                        "image/jpeg"
                    )
                },
                data={
                    "title": "📷 Camera Access Alert",
                    "description": "Camera activated",
                    "severity": "HIGH"
                },
                headers={
                    "X-Agent-ID": config.agent_id,
                    "X-API-Key": config.api_key
                },
                timeout=30
            )

        logger.info("Camera upload: %s", response.status_code)

        # Clean up the temp file
        try:
            os.remove(filename)
        except OSError:
            pass

    except Exception as e:
        logger.error("Camera error: %s", e)


class CameraWatcher:
    """Monitors Android camera usage and triggers alerts."""

    def __init__(self, config, alert_callback):
        self.config = config
        self.alert = alert_callback
        self._running = False
        self._known_camera_packages = [
            "com.android.camera",
            "com.google.android.GoogleCamera",
            "com.sec.android.app.camera",
            "com.android.camera2",
            "org.codeaurora.snapcam",
            "org.lineageos.snap",
        ]

    def start(self):
        self._running = True
        logger.info("Camera watcher started")

    def stop(self):
        self._running = False
        logger.info("Camera watcher stopped")

    def _handle_open(self, package_name: str):
        """Called when a camera app is detected opening."""
        is_suspicious = package_name not in self._known_camera_packages

        if is_suspicious:
            # Take a photo and upload before sending the alert
            take_photo_and_send(self.config, self.alert)

            self.alert({
                "title": "📷 Suspicious Camera Access",
                "description": f"Unknown camera app: {package_name}",
                "severity": "HIGH",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "package": package_name,
                    "suspicious": True
                },
                "agent_id": self.config.agent_id,
                "device_info": {}
            })
        else:
            self.alert({
                "title": "📷 Camera Access",
                "description": f"Camera opened: {package_name}",
                "severity": "MEDIUM",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "package": package_name,
                    "suspicious": False
                },
                "agent_id": self.config.agent_id,
                "device_info": {}
            })

    def on_camera_event(self, package_name: str, event_type: str):
        """Event handler for camera open/close events from the Android log monitor."""
        if event_type == "open":
            self._handle_open(package_name)
        elif event_type == "close":
            logger.debug("Camera closed: %s", package_name)
