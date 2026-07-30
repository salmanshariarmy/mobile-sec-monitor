"""
Camera access monitor.
Detects when apps activate the camera unexpectedly via logcat.
"""

import logging
import re
import subprocess
import threading
import time
import datetime
import os

logger = logging.getLogger("camera_watcher")


class CameraWatcher:

    def __init__(self, alert_callback, config):
        self.alert = alert_callback
        self.config = config
        self.running = False
        self.open_sessions = {}
        self._lock = threading.Lock()


    def get_foreground_app(self) -> str:
        """
        Get currently focused application.
        """

        try:

            output = subprocess.check_output(
                [
                    "dumpsys",
                    "window",
                    "windows"
                ],
                timeout=5,
                text=True,
                stderr=subprocess.DEVNULL
            )


            patterns = [
                r"mCurrentFocus.*?([\w.]+)/",
                r"mFocusedApp.*?([\w.]+)/",
            ]


            for pattern in patterns:

                match = re.search(
                    pattern,
                    output
                )

                if match:
                    return match.group(1)


        except Exception:
            pass


        return "unknown"



    def capture_photo(self):

        """
        Request camera capture.
        Android may require user interaction.
        """

        try:

            filename = (
                f"/sdcard/DCIM/"
                f"security_{int(time.time())}.jpg"
            )


            subprocess.Popen(
                [
                    "am",
                    "start",
                    "-a",
                    "android.media.action.IMAGE_CAPTURE",
                    "--output",
                    filename
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )


            logger.info(
                "Camera capture requested: %s",
                filename
            )


            return filename


        except Exception as e:

            logger.error(
                "Capture failed: %s",
                e
            )

            return None




    def run(self):

        self.running = True


        logger.info(
            "Camera watcher monitoring logcat..."
        )


        try:

            proc = subprocess.Popen(
                [
                    "logcat",
                    "-s",
                    "CameraService",
                    "Camera2Client",
                    "CameraHal",
                    "CamX",
                    "CHIUSECallbacks"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )


        except Exception as e:

            logger.error(
                "Cannot start logcat: %s",
                e
            )

            return



        for line in iter(
            proc.stdout.readline,
            ""
        ):

            if not self.running:
                break


            now = datetime.datetime.utcnow().isoformat()


            open_match = re.search(
                r"Camera\s+(\d+)\s+opened\s+by\s+(?:package\s+)?([^\s,]+)",
                line
            )


            connect_match = re.search(
                r"connect\s*\(\).*Client\s*\(([^)]+)\)",
                line
            )


            close_match = re.search(
                r"Camera\s+(\d+)\s+closed",
                line
            )



            with self._lock:


                if open_match:

                    self._handle_open(
                        open_match.group(1),
                        open_match.group(2),
                        now
                    )


                elif connect_match:

                    self._handle_open(
                        "0",
                        connect_match.group(1),
                        now
                    )


                if close_match:

                    self._handle_close(
                        close_match.group(1),
                        now
                    )





    def _handle_open(
        self,
        cam_id,
        package,
        timestamp
    ):


        foreground = self.get_foreground_app()


        self.open_sessions[cam_id] = {

            "package": package,

            "foreground": foreground,

            "timestamp": timestamp

        }



        if package in self.config.camera_whitelist:

            return



        suspicious = False

        reasons = []



        if package != foreground:

            suspicious = True

            reasons.append(
                f"Background camera access: {package}"
            )



        if suspicious:


            photo = self.capture_photo()



            self.alert({

                "title":
                "📷 Suspicious Camera Access",


                "description":
                "; ".join(reasons),


                "severity":
                "HIGH",


                "timestamp":
                timestamp,


                "details": {

                    "camera_id": cam_id,

                    "package": package,

                    "foreground_app": foreground,

                    "photo_path": photo

                }

            })






    def _handle_close(
        self,
        cam_id,
        timestamp
    ):


        if cam_id not in self.open_sessions:

            return



        session = self.open_sessions[cam_id]


        try:

            start = datetime.datetime.fromisoformat(
                session["timestamp"]
            )


            end = datetime.datetime.fromisoformat(
                timestamp
            )


            duration = (
                end-start
            ).total_seconds()



            if duration < 0.5:


                self.alert({

                    "title":
                    "📷 Brief Camera Access",


                    "description":
                    (
                        f"Camera opened "
                        f"{duration:.2f}s "
                        f"by {session['package']}"
                    ),


                    "severity":
                    "MEDIUM",


                    "timestamp":
                    timestamp,


                    "details": {

                        "camera_id": cam_id,

                        "package":
                        session["package"],

                        "duration":
                        duration

                    }

                })


        except Exception as e:

            logger.error(
                "Close handler error %s",
                e
            )



        del self.open_sessions[cam_id]
