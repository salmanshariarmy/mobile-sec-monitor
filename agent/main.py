#!/usr/bin/env python3

import threading
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from config_builtin import BOT_URL, API_KEY, AGENT_ID


class MonitorUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            spacing=20,
            padding=30,
            **kwargs,
        )

        self.status_label = Label(
            text="Security Monitor\nReady",
            font_size="22sp",
        )
        self.add_widget(self.status_label)

        self.test_button = Button(
            text="Test Render Connection",
            size_hint_y=0.3,
        )
        self.test_button.bind(on_press=self.test_connection)
        self.add_widget(self.test_button)

    def set_status(self, message):
        self.status_label.text = message

    def test_connection(self, _instance=None):
        self.test_button.disabled = True
        self.set_status("Connecting to Render...")

        threading.Thread(
            target=self._connection_worker,
            daemon=True,
        ).start()

    def _connection_worker(self):
        try:
            import requests

            if "your-" in BOT_URL or "CHANGE_THIS" in API_KEY:
                raise ValueError(
                    "BOT_URL or API_KEY is still using a placeholder"
                )

            response = requests.post(
                f"{BOT_URL.rstrip('/')}/agent/heartbeat",
                json={
                    "device_info": {
                        "platform": "android",
                        "status": "APK connection test",
                    }
                },
                headers={
                    "X-API-Key": API_KEY,
                    "X-Agent-ID": AGENT_ID,
                },
                timeout=20,
            )

            message = (
                f"Render response: HTTP {response.status_code}\n"
                f"{response.text[:200]}"
            )

        except Exception:
            message = "Connection failed:\n" + traceback.format_exc()[-700:]

        Clock.schedule_once(
            lambda _dt: self.finish_test(message),
            0,
        )

    def finish_test(self, message):
        self.set_status(message)
        self.test_button.disabled = False


class SecurityMonitorApp(App):
    def build(self):
        return MonitorUI()


if __name__ == "__main__":
    SecurityMonitorApp().run()
