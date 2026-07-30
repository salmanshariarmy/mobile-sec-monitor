#!/usr/bin/env python3

import threading
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from config_builtin import BOT_URL, API_KEY, AGENT_ID
from main_service import run_agent


class AgentConfig:
    bot_url = BOT_URL
    api_key = API_KEY
    agent_id = AGENT_ID


class MonitorUI(BoxLayout):

    def __init__(self, **kwargs):

        super().__init__(
            orientation="vertical",
            spacing=20,
            padding=30,
            **kwargs
        )

        self.status_label = Label(
            text="Security Monitor\nReady",
            font_size="22sp",
        )

        self.add_widget(self.status_label)


        # Heartbeat test button
        self.test_button = Button(
            text="Test Render Connection",
            size_hint_y=0.25,
        )

        self.test_button.bind(
            on_press=self.test_connection
        )

        self.add_widget(self.test_button)


        # Alert test button
        self.alert_button = Button(
            text="Send Test Alert",
            size_hint_y=0.25,
        )

        self.alert_button.bind(
            on_press=self.send_test_alert
        )

        self.add_widget(self.alert_button)



    def set_status(self, message):

        self.status_label.text = message



    # ===============================
    # HEARTBEAT TEST
    # ===============================

    def test_connection(self, _instance=None):

        self.test_button.disabled = True

        self.set_status(
            "Testing heartbeat..."
        )


        threading.Thread(
            target=self._connection_worker,
            daemon=True
        ).start()



    def _connection_worker(self):

        try:

            import requests


            response = requests.post(

                f"{BOT_URL.rstrip('/')}/agent/heartbeat",

                json={
                    "device_info": {
                        "platform": "android",
                        "status": "APK heartbeat test"
                    }
                },

                headers={

                    "X-API-Key": API_KEY,

                    "X-Agent-ID": AGENT_ID,

                    "Content-Type": "application/json",

                },

                timeout=20
            )


            message = (
                f"Heartbeat:\n"
                f"HTTP {response.status_code}\n"
                f"{response.text[:200]}"
            )


        except Exception:

            message = (
                "Heartbeat failed:\n"
                +
                traceback.format_exc()[-700:]
            )


        Clock.schedule_once(

            lambda dt:
            self.finish_test(message),

            0

        )



    # ===============================
    # ALERT TEST
    # ===============================

    def send_test_alert(self, _instance=None):

        self.alert_button.disabled = True

        self.set_status(
            "Sending alert..."
        )


        threading.Thread(

            target=self._alert_worker,

            daemon=True

        ).start()



    def _alert_worker(self):

        try:

            import requests


            response = requests.post(

                f"{BOT_URL.rstrip('/')}/alert",

                json={

                    "title": "APK Test Alert",

                    "description":
                    "Security Monitor test alert from Android",

                    "severity": "HIGH",

                    "device_info": {

                        "agent_id": AGENT_ID,

                        "platform": "android"

                    }

                },

                headers={

                    "X-API-Key": API_KEY,

                    "X-Agent-ID": AGENT_ID,

                    "Content-Type": "application/json"

                },

                timeout=20

            )


            message = (

                f"Alert:\n"

                f"HTTP {response.status_code}\n"

                f"{response.text[:200]}"

            )


        except Exception:

            message = (

                "Alert failed:\n"

                +

                traceback.format_exc()[-700:]

            )


        Clock.schedule_once(

            lambda dt:
            self.finish_alert(message),

            0

        )



    def finish_test(self, message):

        self.set_status(message)

        self.test_button.disabled = False



    def finish_alert(self, message):

        self.set_status(message)

        self.alert_button.disabled = False





class SecurityMonitorApp(App):


    def build(self):

        # Start background monitoring agent

        threading.Thread(

            target=self.start_agent,

            daemon=True

        ).start()


        return MonitorUI()



    def start_agent(self):

        try:

            run_agent(

                AgentConfig()

            )

        except Exception:

            traceback.print_exc()



if __name__ == "__main__":

    SecurityMonitorApp().run()
