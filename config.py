import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.tradovate_username = os.environ["TRADOVATE_USERNAME"]
        self.tradovate_password = os.environ["TRADOVATE_PASSWORD"]
        self.tradovate_app_id = os.environ["TRADOVATE_APP_ID"]
        self.tradovate_app_version = os.environ["TRADOVATE_APP_VERSION"]
        self.tradovate_client_id = int(os.environ["TRADOVATE_CLIENT_ID"])
        self.tradovate_secret = os.environ["TRADOVATE_SECRET"]
        self.tradovate_device_id = os.environ["TRADOVATE_DEVICE_ID"]
        self.tradovate_env = os.environ["TRADOVATE_ENV"]
        self.account_id = int(os.environ["TRADOVATE_ACCOUNT_ID"])
        self.account_spec = os.environ["TRADOVATE_ACCOUNT_SPEC"]
        self.webhook_secret = os.environ["WEBHOOK_SECRET"]
        self.symbol = os.environ["SYMBOL"]
        self.contracts = int(os.environ["CONTRACTS"])
        self.stop_points = int(os.environ["STOP_POINTS"])
        self.max_daily_losses = int(os.environ["MAX_DAILY_LOSSES"])
        self.max_daily_trades = int(os.environ["MAX_DAILY_TRADES"])
        self.close_hour_est = int(os.environ["CLOSE_HOUR_EST"])
        self.close_minute_est = int(os.environ["CLOSE_MINUTE_EST"])

        if self.tradovate_env == "live":
            self.base_url = "https://live.tradovateapi.com/v1"
            self.ws_url = "wss://live.tradovateapi.com/v1/websocket"
        else:
            self.base_url = "https://demo.tradovateapi.com/v1"
            self.ws_url = "wss://demo.tradovateapi.com/v1/websocket"

try:
    settings = Settings()
except KeyError:
    settings = None
