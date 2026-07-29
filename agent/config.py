"""
Agent configuration.
"""
import json
import os
import platform
import subprocess
import re


class AgentConfig:
    def __init__(self, bot_url: str, api_key: str, agent_id: str,
                 scan_interval: int = 30):
        self.bot_url = bot_url
        self.api_key = api_key
        self.agent_id = agent_id
        self.scan_interval = scan_interval

        # Whitelisted camera apps (will not trigger alerts)
        self.camera_whitelist = {
            "com.google.android.apps.camera",
            "com.android.camera",
            "org.codeaurora.snapcam",
            "com.sec.android.app.camera",
            "com.samsung.android.secretmode",  # Samsung Secure Folder camera
            "com.android.server.telecom",
        }

        # Suspicious phone prefixes (premium numbers)
        self.premium_prefixes = ["0900", "1900", "1-900", "0901", "0906", "0907"]

        # SMS URL shortener domains to flag
        self.shortener_domains = [
            "bit.ly", "tinyurl.com", "t.co", "shorturl.at",
            "rb.gy", "ow.ly", "is.gd", "buff.ly", "cli.gs",
            "cur.lv", "soo.gd", "s2r.co", "shorte.st",
        ]

    def get_device_info(self) -> dict:
        """Gather device information for heartbeat."""
        info = {
            "model": platform.machine(),
            "platform": platform.system(),
            "version": platform.version(),
        }
        # Try to get Android-specific info
        try:
            ret = subprocess.run(
                ["getprop", "ro.build.version.sdk"],
                capture_output=True, text=True, timeout=2
            )
            if ret.returncode == 0:
                info["android_sdk"] = ret.stdout.strip()

            ret = subprocess.run(
                ["getprop", "ro.product.manufacturer"],
                capture_output=True, text=True, timeout=2
            )
            if ret.returncode == 0:
                info["manufacturer"] = ret.stdout.strip()

            ret = subprocess.run(
                ["getprop", "ro.product.model"],
                capture_output=True, text=True, timeout=2
            )
            if ret.returncode == 0:
                info["model"] = ret.stdout.strip()
        except Exception:
            pass
        return info
