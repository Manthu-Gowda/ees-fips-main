import os
import logging
from logging.handlers import RotatingFileHandler

# Get project root directory (where ees_logger.py exists)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create logs folder inside project
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Log file path
LOG_FILE = os.path.join(LOG_DIR, "ees_app_logs.log")

# Rotating log: 5MB per file, keep 5 backups
rotating_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        rotating_handler,
        logging.StreamHandler()
    ]
)

ees_logger = logging.getLogger(__name__)