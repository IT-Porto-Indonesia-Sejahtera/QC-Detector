import requests
import json
import time
import hmac
import hashlib
import base64
import os
import traceback
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LarkLoggingHandler(logging.Handler):
    """
    Custom logging handler to send ERROR level logs to Lark.
    """
    def __init__(self, level=logging.ERROR):
        super().__init__(level)
        self.notifier = LarkNotifier()

    def emit(self, record):
        try:
            msg = self.format(record)
            title = f"System {record.levelname}"
            
            # Extract traceback if present in record
            error_details = None
            if record.exc_info:
                error_details = "".join(traceback.format_exception(*record.exc_info))
            
            # Map logging levels to Lark card levels
            level_map = {
                logging.CRITICAL: "crash",
                logging.ERROR: "error",
                logging.WARNING: "warning"
            }
            lark_level = level_map.get(record.levelno, "info")
            
            # If it's a warning, we skip the traceback unless it's explicitly there
            self.notifier.send_interactive_card(
                title=title,
                content=msg,
                level=lark_level,
                error_details=error_details
            )
        except Exception:
            self.handleError(record)

class LarkNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.getenv("LARK_WEBHOOK_URL")
        self.secret = os.getenv("LARK_APP_SECRET")

    def gen_sign(self, timestamp, secret):
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    def send_interactive_card(self, title, content, level="info", error_details=None):
        """
        Send a beautified interactive card to Lark.
        level: "info", "warning", "error", "crash"
        """
        if not self.webhook_url:
            return

        timestamp = int(time.time())
        sign = ""
        if self.secret:
            sign = self.gen_sign(timestamp, self.secret)

        # Map levels to colors
        colors = {
            "info": "blue",
            "warning": "orange",
            "error": "red",
            "crash": "purple"
        }
        header_color = colors.get(level, "blue")

        # Build card payload
        card = {
            "config": {"enable_forward": True, "update_multi": True},
            "header": {
                "template": header_color,
                "title": {"content": f"[{level.upper()}] {title}", "tag": "plain_text"}
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"content": content, "tag": "lark_md"}
                }
            ]
        }

        if error_details:
            card["elements"].append({
                "tag": "hr"
            })
            card["elements"].append({
                "tag": "div",
                "text": {
                    "content": f"**Traceback:**\n```python\n{error_details}\n```",
                    "tag": "lark_md"
                }
            })

        card["elements"].append({
            "tag": "note",
            "elements": [
                {"content": f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", "tag": "plain_text"}
            ]
        })

        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        if sign:
            payload["timestamp"] = str(timestamp)
            payload["sign"] = sign

        try:
            response = requests.post(self.webhook_url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to send Lark card: {e}")
            return False

    def send_text_message(self, text):
        if not self.webhook_url:
            return

        timestamp = int(time.time())
        sign = ""
        if self.secret:
            sign = self.gen_sign(timestamp, self.secret)
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "msg_type": "text",
            "content": {"text": text}
        }
        
        if sign:
            payload["timestamp"] = str(timestamp)
            payload["sign"] = sign
        
        try:
            response = requests.post(self.webhook_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to send Lark message: {e}")
            return False

if __name__ == "__main__":
    notifier = LarkNotifier()
    # Test card
    notifier.send_interactive_card(
        "Test Notification", 
        "This is a **test** message from the enhanced notifier.",
        level="warning",
        error_details="ZeroDivisionError: division by zero\n  File \"main.py\", line 42"
    )