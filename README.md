# 🛡️ Mobile Security Monitor

Real-time mobile threat detection + Discord alert bot.  
Monitors **camera access**, **call logs**, and **SMS** for cybersecurity threats.

## Architecture
┌─────────────────┐ HTTPS/JSON ┌──────────────────┐ │ Android Agent │ ──────────────────> │ Discord Bot │ │ (Termux) │ │ (Python/FastAPI) │ │ - Camera Watch │ │ - Alert Receiver │ │ - Call Monitor │ │ - Slash Commands │ │ - SMS Analyzer │ │ - SQLite Storage │ │ - Network Watch│ │ - Role Pings │ └─────────────────┘ └────────┬─────────┘ │ ▼ ┌──────────────┐ │ Discord API │ │ (Embeds + DM)│ └──────────────┘

## Features

| Module | Detects | Severity |
|---|---|---|
| 📷 Camera Watcher | Background camera access, brief open/close bursts | 🔴 HIGH / 🟡 MED |
| 📞 Call Monitor | Premium-rate numbers, call forwarding codes, repeated missed calls | 🔴 CRIT→LOW |
| 💬 SMS Analyzer | Phishing keywords, suspicious URLs, credential harvesting, smishing | 🔴 CRIT / 🟠 HIGH |
| 🌐 Network Watch | Unexpected connections, data exfiltration patterns | 🟠 HIGH / 🟡 MED |
| 🚨 Discord Bot | Slash commands, real-time embeds, role pings, threat dashboard | All |

## Quick Start

### 1. Discord Bot (Server)

```bash
git clone https://github.com/YOUR_USER/mobile-sec-monitor.git
cd mobile-sec-monitor/bot
cp .env.example .env
# Edit .env with your token & channel ID
pip install -r requirements.txt
python main.py
2. Android Agent (Device)
# On Android via Termux (F-Droid version recommended)
pkg install git python -y
git clone https://github.com/YOUR_USER/mobile-sec-monitor.git
cd mobile-sec-monitor/agent
chmod +x installer.sh
./installer.sh
# Follow prompts for bot URL & agent ID
3. Docker (Production)
docker-compose up -d
Discord Commands


Command	Description
/status	System health + last alert
/alerts recent [count]	Last N alerts
/alerts severity [level]	Filter by severity
/dashboard	Interactive threat dashboard
/summary [hours]	Threat summary chart
/agent status	Ping connected agents
/agent lockdown	Emergency device lockdown
/agent resume	Resume monitoring
/block number	Block a phone number
/whitelist app	Whitelist a camera app
# ── 5. LICENSE ──
cat > LICENSE << 'LICEOF'
MIT License

Copyright (c) 2026 Mobile Security Monitor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
