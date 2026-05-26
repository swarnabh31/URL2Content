import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from config.settings import get_settings

def setup_logging():
    """
    Configures structured logging with both a rotating file handler 
    and a console handler.
    """
    settings = get_settings()
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # File handler with rotation (5MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=5_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Console handler for real-time monitoring
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    
    # Clear existing handlers to avoid duplicate logs during Streamlit reruns
    if root.hasHandlers():
        root.handlers.clear()
        
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    
    logging.info("Logging initialized successfully.")
