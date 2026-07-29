"""
Network traffic anomaly detection.
Monitors active connections and detects data exfiltration patterns.
"""
import logging
import re
import subprocess
import time
import datetime
import socket

logger = logging.getLogger("network_watch")


class NetworkWatcher:
    def __init__(self, alert_callback, config):
        self.alert = alert_callback
        self.config = config
        self.running = False

        # Known C2 / malware endpoints (example list — expand as needed)
        self.suspicious_ips = set()
        self._known_connections = set()

    def get_active_connections(self):
        """Get active TCP/UDP connections via netstat or /proc."""
        connections = []
        try:
            # Try netstat first
            output = subprocess.check_output(
                ["netstat", "-n", "-p", "tcp", "-p", "udp"],
                timeout=5, text=True, stderr=subprocess.DEVNULL
            )
            for line in output.split("\n"):
                parts = line.split()
                if len(parts) >= 5:
                    proto = parts[0]
                    local = parts[3]
                    foreign = parts[4]
                    state = parts[5] if len(parts) > 5 else ""
                    connections.append({
                        "proto": proto,
                        "local": local,
                        "foreign": foreign,
                        "state": state,
                    })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            try:
                # Fallback: /proc/net/tcp
                with open("/proc/net/tcp") as f:
                    for line in f.readlines()[1:]:  # Skip header
                        parts = line.split()
                        if len(parts) >= 10:
                            local_hex = parts[1]
                            remote_hex = parts[2]
                            state_hex = parts[3]
                            connections.append({
                                "proto": "tcp",
                                "local_hex": local_hex,
                                "remote_hex": remote_hex,
                                "state_hex": state_hex,
                            })
            except Exception:
                pass
        return connections

    def _hex_to_ip(self, hex_str):
        """Convert hex IP:port to human-readable."""
        try:
            ip_hex, port_hex = hex_str.split(":")
            ip_parts = [str(int(ip_hex[i:i+2], 16)) for i in range(6, -2, -2)]
            ip = ".".join(ip_parts)
            port = int(port_hex, 16)
            return f"{ip}:{port}"
        except Exception:
            return hex_str

    def analyze_connection(self, conn):
        """Analyze a single connection for suspicious patterns."""
        now = datetime.datetime.utcnow().isoformat()
        alerts = []

        foreign = conn.get("foreign", "")
        if not foreign and "remote_hex" in conn:
            foreign = self._hex_to_ip(conn["remote_hex"])

        if not foreign:
            return alerts

        # Extract IP and port
        match = re.match(r"(\d+\.\d+\.\d+\.\d+):(\d+)", foreign)
        if not match:
            return alerts

        ip, port = match.group(1), int(match.group(2))

        # 1. Check for connections to suspicious ports
        suspicious_ports = {
            4444: "Metasploit default",
            4445: "Metasploit",
            5555: "Android ADB",
            8080: "Common proxy",
            1337: "Common C2",
            31337: "Back Orifice",
            12345: "NetBus",
            27374: "SubSeven",
        }

        if port in suspicious_ports:
            alerts.append({
                "title": "🌐 Connection to Suspicious Port",
                "description": f"Connection to {ip}:{port} ({suspicious_ports[port]})",
                "severity": "HIGH",
                "timestamp": now,
                "details": {
                    "remote": foreign,
                    "port": port,
                    "known_service": suspicious_ports[port],
                }
            })

        # 2. Check for connections to private/loopback that shouldn't be there
        if ip.startswith("127.") or ip.startswith("0."):
            # Loopback is normal
            pass
        elif ip.startswith("10.") or ip.startswith("172.16.") or ip.startswith("192.168."):
            # Private IPs are normal for LAN
            pass
        elif ip in self.suspicious_ips:
            alerts.append({
                "title": "🌐 Connection to Known Malicious IP",
                "description": f"Connection to flagged IP: {ip}:{port}",
                "severity": "CRITICAL",
                "timestamp": now,
                "details": {
                    "remote": foreign,
                }
            })

        # 3. Detect many connections to same IP (potential data exfiltration)
        conn_key = f"{ip}:{port}"
        if conn_key in self._known_connections:
            self._known_connections[conn_key] += 1
            if self._known_connections[conn_key] > 10:
                alerts.append({
                    "title": "🌐 Multiple Connections to Same Endpoint",
                    "description": f"{self._known_connections[conn_key]} connections to {ip}:{port}",
                    "severity": "MEDIUM",
                    "timestamp": now,
                    "details": {
                        "remote": foreign,
                        "count": self._known_connections[conn_key],
                        "possible": "Data exfiltration"
                    }
                })
        else:
            self._known_connections[conn_key] = 1

        return alerts

    def run(self):
        self.running = True
        logger.info("Network watcher started")

        while self.running:
            try:
                connections = self.get_active_connections()
                for conn in connections[-20:]:  # Check recent connections
                    alerts = self.analyze_connection(conn)
                    for a in alerts:
                        self.alert(a)

                # Clean up connection tracker
                if len(self._known_connections) > 1000:
                    self._known_connections.clear()

            except Exception as e:
                logger.debug(f"Network scan error: {e}")

            time.sleep(self.config.scan_interval * 2)  # Network scans less frequently
