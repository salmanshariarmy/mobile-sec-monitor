"""
Call log monitor.
Detects premium numbers, call forwarding, repeated missed calls.
"""
import logging
import re
import subprocess
import time
import datetime

import phonenumbers

logger = logging.getLogger("call_monitor")


class CallMonitor:
    def __init__(self, alert_callback, config):
        self.alert = alert_callback
        self.config = config
        self.running = False
        self.known_calls = set()
        self.call_history = []

    def get_call_log(self, limit=50):
        """Pull recent call log via Android content provider."""
        try:
            output = subprocess.check_output(
                ["content", "query", "--uri", "content://call_log/calls",
                 "--projection", "number:date:duration:type:countryiso:name",
                 "--limit", str(limit)],
                timeout=10, text=True, stderr=subprocess.DEVNULL
            )
            return self._parse(output)
        except Exception as e:
            logger.debug(f"Error reading call log: {e}")
            return []

    def _parse(self, output):
        calls = []
        for line in output.strip().split("\n"):
            if not line.startswith("Row:"):
                continue
            record = {}
            parts = line.split()
            for part in parts[2:]:
                if "=" in part:
                    key, val = part.split("=", 1)
                    record[key] = val
            if "number" in record:
                calls.append(record)
        return calls

    def analyze(self, call):
        """Analyze a single call record. Returns list of alerts."""
        number = call.get("number", "")
        duration = int(call.get("duration", "0"))
        call_type = int(call.get("type", "0"))  # 1=in, 2=out, 3=missed
        now = datetime.datetime.utcnow().isoformat()
        type_label = ["unknown", "incoming", "outgoing", "missed"][call_type] if 1 <= call_type <= 3 else "unknown"
        alerts = []

        # 1. Premium rate numbers
        for prefix in self.config.premium_prefixes:
            if number.startswith(prefix):
                alerts.append({
                    "title": "💰 Premium-Rate Call Detected",
                    "description": f"Call to/from premium number {number}",
                    "severity": "HIGH",
                    "timestamp": now,
                    "details": {
                        "number": number,
                        "duration_sec": duration,
                        "type": type_label,
                    }
                })
                break

        # 2. Call forwarding codes
        forward_patterns = [r"\*\*21\*", r"\*21\*", r"\*67\*", r"\*72\*",
                            r"\*73\*", r"\*\*004\*", r"\*\*61\*", r"\*\*62\*", r"\*\*67\*"]
        for pat in forward_patterns:
            if re.search(pat, number):
                alerts.append({
                    "title": "🔄 Call Forwarding Detected",
                    "description": f"Call forwarding code in dialed number: {number}",
                    "severity": "CRITICAL",
                    "timestamp": now,
                    "details": {
                        "number": number,
                        "code": pat,
                        "warning": "Possible call interception setup"
                    }
                })
                break

        # 3. Invalid/unknown number format
        if number and number not in ("-1", "private", "blocked", "unknown", ""):
            try:
                parsed = phonenumbers.parse(number, None)
                if not phonenumbers.is_valid_number(parsed):
                    alerts.append({
                        "title": "❓ Invalid Number Format",
                        "description": f"Call from/to invalid number: {number}",
                        "severity": "LOW",
                        "timestamp": now,
                        "details": {"number": number, "type": type_label}
                    })
            except phonenumbers.NumberParseException:
                pass

        # 4. Repeated missed calls (potential canary)
        if duration == 0 and call_type == 3:  # Missed, zero duration
            recent = [c for c in self.call_history[-20:]
                      if c.get("number") == number and
                      int(c.get("duration", 0)) == 0 and
                      int(c.get("type", 0)) == 3]
            if len(recent) >= 3:
                alerts.append({
                    "title": "🔔 Repeated Missed Calls",
                    "description": f"Number {number} has called {len(recent)+1} times without answer",
                    "severity": "MEDIUM",
                    "timestamp": now,
                    "details": {
                        "number": number,
                        "missed_count": len(recent) + 1,
                        "possible": "Canary call / surveillance check"
                    }
                })

        return alerts

    def run(self):
        self.running = True
        logger.info("Call monitor started")

        while self.running:
            try:
                calls = self.get_call_log(limit=50)
                for call in calls:
                    call_id = f"{call.get('number', '')}:{call.get('date', '')}"
                    if call_id in self.known_calls:
                        continue
                    self.known_calls.add(call_id)
                    if len(self.known_calls) > 10000:
                        self.known_calls.clear()

                    alerts = self.analyze(call)
                    for a in alerts:
                        self.alert(a)

                self.call_history = calls + self.call_history
                self.call_history = self.call_history[:500]

            except Exception as e:
                logger.error(f"Call scan error: {e}")

            time.sleep(self.config.scan_interval)
