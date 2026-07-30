# 🛡️ Mobile Security Monitor

Monitor your Android phone from anywhere in the world via Discord.
Camera alerts, call monitoring, SMS analysis, network watch.

## How It Works
Your Phone (APK) ──HTTPS──> Render (Bot Server) ──Discord API──> Your Discord Channel

## Quick Start

### 1. Deploy Bot on Render (5 min, free)

1. Go to [render.com](https://render.com) → Sign up with GitHub (no credit card needed)
2. Click **New +** → **Web Service**
3. Connect your GitHub repo: `salmanshariarmy/mobile-sec-monitor`
4. Set:
   - **Name**: `mobile-sec-monitor`
   - **Runtime**: `Docker`
   - **Instance Type**: **Free**
5. Click **Advanced** → **Add Environment Variable**:
   - `DISCORD_BOT_TOKEN` — Your Discord bot token
   - `GUILD_ID` — Your Discord server ID
   - `ALERT_CHANNEL_ID` — Channel where alerts appear
   - `HTTP_API_KEY` — Random secret key (use the same one in your APK)
6. Click **Create Web Service**
7. Your bot is live at `https://mobile-sec-monitor.onrender.com`

### 2. Build APK (20 min)

```bash
sudo apt install -y git python3 python3-pip openjdk-17-jdk-headless
pip install buildozer cython
git clone https://github.com/salmanshariarmy/mobile-sec-monitor.git
cd mobile-sec-monitor

# Build
buildozer android debug

# APK at: bin/SecurityMonitor-1.0.0-arm64-v8a-debug.apk

3. Install on Phone → Grant Permissions → Done

Discord Commands

Command	Description
/status	System health
/alerts recent 10	Last 10 alerts
/dashboard	Interactive stats
/summary 24	Last 24h summary
/agent lockdown	Emergency stop
/agent resume	Resume monitoring
