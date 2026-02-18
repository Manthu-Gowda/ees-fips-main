import os, logging
from logging.handlers import RotatingFileHandler
LOG_FILE = r"C:\Users\Administrator\Documents\ees\logs\ees_app_logs.log"

if not os.path.exists(os.path.dirname(LOG_FILE)):
    os.makedirs(os.path.dirname(LOG_FILE))

# Setup Rotating Handler: 5MB per file, keeps 3 old backups
# 5 * 1024 * 1024 bytes = 5MB
rotating_handler = RotatingFileHandler(
    LOG_FILE, 
    maxBytes=5*1024*1024, 
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