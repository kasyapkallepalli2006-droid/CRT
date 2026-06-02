import logging
import os
from datetime import datetime

def setup_logger():
    """
    Sets up application-wide logger.
    Logs to both console and a file.
    """
    os.makedirs('logs', exist_ok=True)

    log_filename = f"logs/app_{datetime.now().strftime('%Y-%m-%d')}.log"

    log_format = (
        "%(asctime)s | %(levelname)s | %(module)s | %(message)s"
    )

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # Write to file
            logging.FileHandler(log_filename),
            # Also print to console
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Logger initialized successfully")
    return logger
logger = setup_logger()