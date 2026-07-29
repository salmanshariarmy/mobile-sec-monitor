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

logger = logging.getLogger("camera_watcher")


class CameraWatcher:
    def __init__(self, alert_callback, config):
        self.alert = alert_callback
        self.config = config
        self.running = False
        self.open_sessions = {}
        self._lock = threading.Lock()

    def get_foreground_app(self) -> str:
        """Get the currently focused app package."""
        try:
            output = subprocess.check_output(
                ["dumpsys", "window", "windows"],
                timeout=5, text=True, stderr=subprocess.DEVNULL
            )
            # Try multiple patterns
            for pattern in [
                r"mCurrentFocus.*?([\w.]+)/",
                r"mFocusedApp.*?([\w.]+)/",
                r"mInputMethod.*?([\w.]+)/",
            ]:
                match = re.search(pattern, output)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return "unknown"

    def run(self):
        """Continuously monitor logcat for camera events."""
        self.running = True

        # Start logcat with camera filters
        try:
            proc = subprocess.Popen(
                ["logcat", "-s", "CameraService", "Camera2Client",
                 "CameraHal", "CamX", "CHIUSECallbacks"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1,
            )
        except FileNotFoundError:
            logger.error("logcat not available — camera monitoring disabled")
            return

        logger.info("Camera watcher monitoring logcat...")

        for line in iter(proc.stdout.readline, ""):
            if not self.running:
                break

            # Pattern 1: Camera opened by package
            open_match = re.search(
                r"Camera\s+(\d+)\s+opened\s+by\s+(?:package\s+)?([^\s,]+)",
                line
            )
            # Pattern 2: connect() called by package
            connect_match = re.search(
                r"connect\s*\(\)\s*.*Client\s*\(([^)]+)\)",
                line
            )
            # Pattern 3: Stream configuration (indicates active camera use)
            stream_match = re.search(
                r"configureStreams.*Camera\s+(\d+)\s+.*?([\w.]+)",
                line
            )

            now = datetime.datetime.utcnow().isoformat()

            with self._lock:
                if open_match:
                    self._handle_open(open_match.group(1), open_match.group(2), now)
                elif connect_match:
                    self._handle_open("0", connect_match.group(1), now)
                elif stream_match:
                    self._handle_open(stream_match.group(1), stream_match.group(2), now)

                # Check for close patterns
                close_match = re.search(r"Camera\s+(\d+)\s+closed", line)
                if close_match:
                    self._handle_close(close_match.group(1), now)

    def _handle_open(self, cam_id: str, package: str, timestamp: str):
        """Process a camera open event."""
        foreground = self.get_foreground_app()
        self.open_sessions[cam_id] = {
            "package": package,
            "foreground": foreground,
            "timestamp": timestamp,
        }

        # Determine if suspicious
        is_suspicious = False
        reasons = []

        # Check if package is whitelisted
        if package in self.config.camera_whitelist:
            return  # All good

        # Background access
        if package != foreground:
            is_suspicious = True
            reasons.append(f"Background access by {package} (foreground: {foreground})")

        # Unknown package accessing camera
        if not package.startswith("com.") and not package.startswith("org."):
            is_suspicious = True
            reasons.append(f"Non-standard package: {package}")

        if is_suspicious:
            self.alert({
                "title": "📷 Suspicious Camera Access",
                "description": "; ".join(reasons),
                "severity": "HIGH",
                "timestamp": timestamp,
                "details": {
                    "camera_id": cam_id,
                    "package": package,
                    "foreground_app": foreground,
                }
            })

    def _handle_close(self, cam_id: str, timestamp: str):
        """Process a camera close event and detect brief access."""
        if cam_id in self.open_sessions:
            session = self.open_sessions[cam_id]
            try:
                start_ts = datetime.datetime.fromisoformat(session["timestamp"])
                end_ts = datetime.datetime.fromisoformat(timestamp)
                duration = (end_ts - start_ts).total_seconds()

                if 0 < duration < 0.5:  # Brief access (< 0.5s)
                    self.alert({
                        "title": "📷 Brief Camera Access",
                        "description": f"Camera {cam_id} opened for {duration:.2f}s by {session['package']}",
                        "severity": "MEDIUM",
                        "timestamp": timestamp,
                        "details": {
                            "camera_id": cam_id,
                            "package": session["package"],
                            "duration_sec": round(duration, 2),
                        }
                    })
            except Exception:
                pass
            del self.open_sessions[cam_id]
