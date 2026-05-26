import logging
import sys
from pathlib import Path
from config import get_settings

def setup_logging(log_dir_path: str = "./logs"):
    """
    Configures centralized logging for the application.
    Logs are sent to both a rotating file and the system console.
    """
    settings = get_settings()
    log_dir = Path(log_dir_path)
    log_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # File handler with rotation (5MB per file, 5 backups)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=5_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)
