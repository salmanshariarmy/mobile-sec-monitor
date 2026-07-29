# 🛡️ Mobile Security Monitor

Monitor your Android phone from anywhere in the world via Discord.
Camera alerts, call monitoring, SMS analysis, network watch.

## How It Works
Your Phone (APK) ──HTTPS──> Railway (Bot Server) ──Discord API──> Your Discord Channel
## Quick Start

### 1. Deploy Bot on Railway (5 min, free)

[Click here to deploy](https://railway.app/new) → Select this repo → Set environment variables below → Done

Required Variables:
- `DISCORD_BOT_TOKEN` - Your Discord bot token
- `GUILD_ID` - Your Discord server ID
- `ALERT_CHANNEL_ID` - Channel where alerts appear
- `HTTP_API_KEY` - Random secret key

### 2. Build APK (20 min)

```bash
sudo apt install -y git python3 python3-pip openjdk-17-jdk-headless
pip install buildozer cython
git clone https://github.com/YOUR_USER/mobile-sec-monitor.git
cd mobile-sec-monitor

# Edit your server URL
nano agent/config_builtin.py

# Build
buildozer android debug

# APK at: bin/SecurityMonitor-1.0.0-arm64-v8a-debug.apk
3. Install on Phone → Grant Permissions → Done
Command	Description
/status	System health
/alerts recent 10	Last 10 alerts
/dashboard	Interactive stats
/summary 24	Last 24h summary
/agent lockdown	Emergency stop
/agent resume	Resume monitoring

License MIT

---

## FILE 3: `buildozer.spec` (Repo Root)

```ini
[app]
title = Security Monitor
package.name = secmonitor
package.domain = com.yourorg.security
source.dir = agent/
source.include_exts = py,png,jpg,kv,atlas,txt,json,xml
requirements = python3,requests,phonenumbers,android,pyjnius,kivy

version = 1.0.0
version.code = 1

presplash.filename = agent/data/presplash.png
icon.filename = agent/data/icon.png
orientation = portrait
fullscreen = 0

android.permissions = \
    CAMERA, \
    READ_CALL_LOG, \
    READ_SMS, \
    RECEIVE_SMS, \
    READ_PHONE_STATE, \
    INTERNET, \
    ACCESS_NETWORK_STATE, \
    ACCESS_WIFI_STATE, \
    FOREGROUND_SERVICE, \
    FOREGROUND_SERVICE_DATA_SYNC, \
    RECEIVE_BOOT_COMPLETED, \
    POST_NOTIFICATIONS, \
    WAKE_LOCK

android.api = 34
android.minapi = 26
android.sdk = 34
android.ndk = 27b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.manifest = agent/AndroidManifest.xml
android.presplash_color = #1a1a2e
android.log_loglevel = 2
android.copy_libs = 1
android.p4a_branch = master
android.enable_androidx = True
android.use_gradle = True
android.gradle_plugin_version = 8.2.0

build.dir = build/
bin.dir = bin/
