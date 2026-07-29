#!/usr/bin/env python3
"""
Mobile Security Monitor — Android APK Entry Point
Starts the foreground service with Kivy UI on launch.
"""
import os
import sys
import threading
import logging

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")

# ── Import built-in config (YOU edit this before building) ──
from config_builtin import BOT_URL, API_KEY, AGENT_ID, SCAN_INTERVAL

# ── Android service ──
from jnius import autoclass

Service = autoclass('org.kivy.android.service.BasicService')
PythonActivity = autoclass('org.kivy.android.PythonActivity')

# ── Start the actual agent in background ──
def start_agent_service():
    """Start the background monitoring agent."""
    from config import AgentConfig
    from main_service import run_agent

    config = AgentConfig(
        bot_url=BOT_URL,
        api_key=API_KEY,
        agent_id=AGENT_ID,
        scan_interval=SCAN_INTERVAL,
    )

    logger.info(f"🚀 Starting agent: {AGENT_ID}")
    logger.info(f"📡 Bot URL: {BOT_URL}")
    
    t = threading.Thread(target=run_agent, args=(config,), daemon=True)
    t.start()

# ── Kivy UI (shown when user opens the app) ──
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock

class MonitorUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', spacing=20, padding=30, **kwargs)
        
        # Title
        title = Label(
            text="🛡️ Security Monitor",
            font_size='28sp',
            bold=True,
            size_hint_y=0.2
        )
        self.add_widget(title)

        # Status
        self.status_label = Label(
            text="Status: Starting...",
            font_size='18sp',
            size_hint_y=0.15
        )
        self.add_widget(self.status_label)

        # Config info
        self.info_label = Label(
            text=f"Agent: {AGENT_ID}\nServer: {BOT_URL}",
            font_size='14sp',
            size_hint_y=0.2,
            text_size=(400, None),
            halign='center'
        )
        self.add_widget(self.info_label)

        # Start button
        self.start_btn = Button(
            text="✅ Start Monitoring",
            font_size='20sp',
            size_hint_y=0.2,
            background_color=(0.2, 0.7, 0.2, 1),
            on_press=self.start_monitoring
        )
        self.add_widget(self.start_btn)

        # Stop button
        self.stop_btn = Button(
            text="⏹️ Stop Monitoring",
            font_size='20sp',
            size_hint_y=0.2,
            background_color=(0.7, 0.2, 0.2, 1),
            disabled=True,
            on_press=self.stop_monitoring
        )
        self.add_widget(self.stop_btn)

        # Agent is running — update status
        Clock.schedule_once(self.check_status, 1)

    def check_status(self, dt):
        self.status_label.text = "Status: ✅ Monitoring Active"
        self.status_label.color = (0, 1, 0, 1)
        self.start_btn.disabled = True
        self.stop_btn.disabled = False

    def start_monitoring(self, instance):
        try:
            start_agent_service()
            self.status_label.text = "Status: ✅ Monitoring Active"
            self.status_label.color = (0, 1, 0, 1)
            self.start_btn.disabled = True
            self.stop_btn.disabled = False
        except Exception as e:
            popup = Popup(title="Error",
                content=Label(text=str(e)),
                size_hint=(0.8, 0.4))
            popup.open()

    def stop_monitoring(self, instance):
        # Stop the service
        try:
            mActivity = PythonActivity.mActivity
            mActivity.stopService(
                autoclass('android.content.Intent')(mActivity, Service)
            )
        except:
            pass
        self.status_label.text = "Status: ⏹️ Stopped"
        self.status_label.color = (1, 0, 0, 1)
        self.start_btn.disabled = False
        self.stop_btn.disabled = True


class SecurityMonitorApp(App):
    def build(self):
        # Auto-start monitoring when app opens
        Clock.schedule_once(lambda dt: start_agent_service(), 2)
        return MonitorUI()


if __name__ == "__main__":
    SecurityMonitorApp().run()
