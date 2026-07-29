#!/data/data/com.termux/files/usr/bin/bash
"""
Mobile Security Monitor — Termux Installer
Run: bash installer.sh
"""

set -e

echo "╔══════════════════════════════════════════╗"
echo "║   Mobile Security Monitor — Installer    ║"
echo "╚══════════════════════════════════════════╝"

# Check Termux
if [ ! -d "/data/data/com.termux" ]; then
    echo "❌ This script must run inside Termux on Android."
    exit 1
fi

echo ""
echo "[*] Updating packages..."
pkg update -y && pkg upgrade -y

echo ""
echo "[*] Installing dependencies..."
pkg install -y python git termux-api util-linux which

echo ""
echo "[*] Installing Python packages..."
pip install requests phonenumbers

echo ""
echo "[*] Setting up storage access..."
termux-setup-storage 2>/dev/null || true

echo ""
echo "┌──────────────────────────────────────────┐"
echo "│ Configuration                            │"
echo "└──────────────────────────────────────────┘"
echo ""

read -p "Enter Discord Bot URL (e.g., http://192.168.1.100:7879): " BOT_URL
read -p "Enter API Key: " API_KEY
read -p "Enter Agent ID (default: android-$(hostname)): " AGENT_ID
AGENT_ID=${AGENT_ID:-android-$(hostname)}
read -p "Scan interval in seconds (default: 30): " SCAN_INTERVAL
SCAN_INTERVAL=${SCAN_INTERVAL:-30}

# Write config to environment file
mkdir -p ~/.mobile-sec-monitor
cat > ~/.mobile-sec-monitor/.env << EOF
BOT_URL=$BOT_URL
API_KEY=$API_KEY
AGENT_ID=$AGENT_ID
SCAN_INTERVAL=$SCAN_INTERVAL
EOF

echo ""
echo "[*] Testing connection to bot..."
if curl -s -X GET "$BOT_URL/health" > /dev/null 2>&1; then
    echo "✅ Bot reachable!"
else
    echo "⚠️  Warning: Cannot reach bot at $BOT_URL (you can fix later)"
fi

echo ""
echo "┌──────────────────────────────────────────┐"
echo "│ Installation Complete!                   │"
echo "└──────────────────────────────────────────┘"
echo ""
echo "To start monitoring:"
echo "  cd mobile-sec-monitor/agent"
echo "  python main.py --bot-url $BOT_URL --api-key $API_KEY --agent-id $AGENT_ID"
echo ""
echo "To run in background (auto-restart):"
echo "  nohup python main.py ... &"
echo ""
echo "To add to Termux:Boot (auto-start on device boot):"
echo "  1. pkg install termux-services"
echo "  2. Create start script in ~/.termux/boot/"
