import os
import json
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.header import Header
from decouple import config as ENV_CONFIG
from video.SESClient import SESClient

# === Configuration ===
DIAGNOSTIC_FILES = {
    "HUD-C": r"C:\Users\Administrator\Documents\ees\media\upload\uploads\Diagnostic\__HUD-C_Diagnostic.json",
    "KRSY-C": r"C:\Users\Administrator\Documents\ees\media\upload\uploads\Diagnostic\__KRSY-C_Diagnostic.json",
}

STATE_FILE = r"C:\Users\Administrator\Documents\ees\scripts\diagnostic_state.json"
LOG_FILE = r"C:\Users\Administrator\Documents\ees\scripts\diagnostic_monitor.log"

EMAIL_RECIPIENTS = ["leah@emergentenforcement.com", "rsarpy@emergentenforcement.com","craig@emergentenforcement.com", "russeljr@emergentenforcement.com"]
EMAIL_CC = ["raju.v@globaldigitalnext.com", "sumith.b@globaldigitalnext.com", "tejas.g@globaldigitalnext.com", "karthik.k@globaldigitalnext.com"]

ALERT_INTERVAL_MINUTES = 30

# === Logging ===
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error("Failed to load state file: %s", e)
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logging.error("Failed to save state file: %s", e)

def send_email(subject, body):
    try:
        ses_client = SESClient()
        response = ses_client.send_email_with_attachment(
            subject=subject,
            body=body,
            to_addresses=EMAIL_RECIPIENTS,
            cc_addresses=EMAIL_CC,
        )
        logging.info("Email subject: %s", subject)
        logging.info(f"Email sent via SES. Message ID: {response['MessageId']}")
    except Exception as e:
        logging.error("Failed to send email: %s", str(e))

def monitor_file(camera_name, file_path, state):
    now = datetime.now()

    if os.path.exists(file_path):
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
        time_diff = now - last_modified

        logging.info("%s file OK. Last modified: %s (%.2f minutes ago)", camera_name, last_modified, time_diff.total_seconds() / 60)

        if time_diff > timedelta(minutes=ALERT_INTERVAL_MINUTES):
            if not state.get(camera_name, {}).get("alert_sent"):
                send_email(
                    subject=f"🚨 Camera Offline Alert: {camera_name}",
                    body=f"{camera_name} diagnostic file has not updated since {last_modified}.\n\nChecked at {now}."
                )
                state[camera_name] = {"alert_sent": True, "last_alert_time": now.isoformat()}
        else:
            if state.get(camera_name, {}).get("alert_sent"):
                send_email(
                    subject=f"✅ Camera Back Online: {camera_name}",
                    body=f"{camera_name} diagnostic file resumed updates at {last_modified}.\nCamera is back online."
                )
                state[camera_name] = {"alert_sent": False, "last_alert_time": None}
    else:
        logging.warning("%s file NOT found: %s", camera_name, file_path)

    return state

def monitor_diagnostic_files():
    state = load_state()
    for camera, file_path in DIAGNOSTIC_FILES.items():
        state = monitor_file(camera, file_path, state)
    save_state(state)

if __name__ == "__main__":
    try:
        monitor_diagnostic_files()
    except Exception as e:
        logging.error("Script Error: %s", str(e))