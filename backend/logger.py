import logging
import os

LOG_DIR = "logs"
LOG_FILE = "privguard.log"

# Ensure logs directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def get_logger():
    return logging.getLogger("PrivGuardLogger")
