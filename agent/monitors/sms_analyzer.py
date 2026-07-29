"""
SMS content analyzer — phishing, credential harvesting, smishing detection.
"""
import logging
import re
import subprocess
import time
import datetime
import urllib.parse

logger = logging.getLogger("sms_analyzer")


class SMSAnalyzer:
    def __init__(self, alert_callback, config):
        self.alert = alert_callback
        self.config = config
        self.running = False
        self.known_sms = set()

    def get_sms(self, limit=50):
        """Pull recent SMS inbox via content provider."""
        try:
            output = subprocess.check_output(
                ["content", "query", "--uri", "content://sms/inbox",
                 "--projection", "address:body:date:date_sent:read:person",
                 "--limit", str(limit)],
                timeout=10, text=True, stderr=subprocess.DEVNULL
            )
            return self._parse(output)
        except Exception as e:
            logger.debug(f"Error reading SMS: {e}")
            return []

    def _parse(self, output):
        msgs = []
        for line in output.strip().split("\n"):
            if not line.startswith("Row:"):
                continue
            record = {}
            parts = line.split()
            for part in parts[2:]:
                if "=" in part:
                    key, val = part.split("=", 1)
                    record[key] = val
            if "address" in record and "body" in record:
                msgs.append(record)
        return msgs

    def analyze(self, msg):
        """Analyze an SMS for threats. Returns list of alerts."""
        body = msg.get("body", "")
        address = msg.get("address", "")
        now = datetime.datetime.utcnow().isoformat()
        alerts = []

        if not body:
            return alerts

        # ── 1. Phishing keyword patterns ──
        phishing_keywords = [
            # Account security
            (r"(?i)\b(verify|confirm)\s*(your|the)\s*(account|identity)", "Account verification request"),
            (r"(?i)\b(account.*suspend|account.*block|account.*lock)", "Account suspension threat"),
            (r"(?i)\b(unauthorized|suspicious)\s*(login|access|attempt)", "Suspicious login alert"),
            (r"(?i)\b(reset|change|update)\s*(your|the)\s*(password|passwd|pin)", "Password reset request"),
            # Payment
            (r"(?i)\b(update|verify|confirm)\s*(payment|billing|credit.card)", "Payment update scam"),
            (r"(?i)\b(claim|won|winner)\s*(reward|prize|gift|lottery)", "Prize/winning scam"),
            # Urgency
            (r"(?i)\b(immediate|urgent|action.required|time.sensitive)", "Urgency pressure tactic"),
            (r"(?i)\b(click.*here|tap.*here|follow.*link)\s*(to|and)", "Click-bait call to action"),
        ]

        for pattern, label in phishing_keywords:
            if re.search(pattern, body):
                alerts.append({
                    "title": "🎣 Phishing Keywords Detected",
                    "description": f"SMS from {address}: {label}",
                    "severity": "CRITICAL",
                    "timestamp": now,
                    "details": {
                        "sender": address,
                        "pattern": label,
                        "body_preview": body[:200],
                    }
                })
                break  # One phish alert per SMS

        # ── 2. URL detection & analysis ──
        url_pattern = re.compile(
            r"https?://[^\s<>\"']+|bit\.ly/[a-zA-Z0-9]+|tinyurl\.com/[a-zA-Z0-9]+"
            r"|t\.co/[a-zA-Z0-9]+|shorturl\.at/[a-zA-Z0-9]+"
            r"|rb\.gy/[a-zA-Z0-9]+|ow\.ly/[a-zA-Z0-9]+|is\.gd/[a-zA-Z0-9]+"
        )
        urls = url_pattern.findall(body)

        if urls:
            suspicious_tlds = {".xyz", ".top", ".loan", ".click", ".work",
                               ".gq", ".ml", ".tk", ".cf", ".ga", ".download",
                               ".review", ".stream", ".bid", ".date"}
            suspicious_urls = []

            for url in urls:
                # Check TLD
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc or parsed.path
                for tld in suspicious_tlds:
                    if domain.endswith(tld):
                        suspicious_urls.append(f"{url} (suspicious TLD: {tld})")
                        break
                # IP-based URL
                if re.search(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", url):
                    suspicious_urls.append(f"{url} (IP-based, no domain)")

            if suspicious_urls:
                alerts.append({
                    "title": "🔗 Suspicious URL in SMS",
                    "description": f"SMS from {address} contains {len(suspicious_urls)} suspicious URL(s)",
                    "severity": "HIGH",
                    "timestamp": now,
                    "details": {
                        "sender": address,
                        "urls": "\n".join(suspicious_urls[:5]),
                        "body_preview": body[:200],
                    }
                })

            # Check for shortened URLs (smishing indicator)
            for domain in self.config.shortener_domains:
                if domain in body.lower():
                    alerts.append({
                        "title": "🔗 Shortened URL (Potential Smishing)",
                        "description": f"SMS from {address} uses URL shortener {domain}",
                        "severity": "MEDIUM",
                        "timestamp": now,
                        "details": {
                            "sender": address,
                            "shortener": domain,
                            "url": urls[0] if urls else "unknown",
                            "body_preview": body[:200],
                        }
                    })
                    break

        # ── 3. Credential harvesting ──
        credential_patterns = [
            r"(?i)(username|password|passwd|login|signin)\s*[:\s]",
            r"(?i)enter\s*(your|the)\s*(credentials|password|pin|otp|code)",
            r"(?i)(otp|one.?time.?pin|2fa|mfa|two.?factor)\s*[:\s]",
            r"(?i)(bank|credit|debit)\s*(account|card|detail).*\d",
        ]
        for pattern in credential_patterns:
            if re.search(pattern, body):
                alerts.append({
                    "title": "🔑 Credential Harvesting Attempt",
                    "description": f"SMS from {address} requests credentials/OTP",
                    "severity": "CRITICAL",
                    "timestamp": now,
                    "details": {
                        "sender": address,
                        "pattern": pattern,
                        "body_preview": body[:200],
                    }
                })
                break

        # ── 4. SMS with just a link (common smishing pattern) ──
        if urls and len(body.strip()) < 100:
            # Message is almost entirely a URL
            alerts.append({
                "title": "📩 Minimal SMS with URL",
                "description": f"SMS from {address} contains only a URL — potential smishing",
                "severity": "MEDIUM",
                "timestamp": now,
                "details": {
                    "sender": address,
                    "body": body[:200],
                }
            })

        return alerts

    def run(self):
        self.running = True
        logger.info("SMS analyzer started")

        while self.running:
            try:
                msgs = self.get_sms(limit=50)
                for msg in msgs:
                    msg_id = f"{msg.get('address', '')}:{msg.get('date', '')}"
                    if msg_id in self.known_sms:
                        continue
                    self.known_sms.add(msg_id)
                    if len(self.known_sms) > 10000:
                        self.known_sms.clear()

                    alerts = self.analyze(msg)
                    for a in alerts:
                        self.alert(a)

            except Exception as e:
                logger.error(f"SMS scan error: {e}")

            time.sleep(self.config.scan_interval)
