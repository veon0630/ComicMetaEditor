import logging
import sys
import os
from pathlib import Path
from datetime import datetime

def setup_logger(name="ComicMetaEditor"):
    """
    Setup a centralized logger.
    Logs to console and file.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    # Prevent propagation to root logger to avoid duplicate output
    logger.propagate = False
    
    # Create logs directory if not exists
    log_dir = Path("logs")
    if not log_dir.exists():
        try:
            log_dir.mkdir(exist_ok=True)
        except Exception:
            # Fallback to current dir if permission denied
            log_dir = Path(".")

    # File Handler
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Global logger instance
logger = setup_logger()
