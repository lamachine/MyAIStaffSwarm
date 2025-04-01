#  Logging and debugging configuration. 
########################

import logging
import os
from datetime import datetime
import pytz
from typing import Dict, Optional
from enum import Enum

# Create custom logging level for VERBOSE
VERBOSE_LEVEL = 15  # Between DEBUG (10) and INFO (20)
logging.addLevelName(VERBOSE_LEVEL, "VERBOSE")

class LogLevel(str, Enum):
    """Logging levels with descriptive names"""
    MINIMAL = "MINIMAL"     # ERROR only
    BASIC = "BASIC"        # ERROR and WARNING
    STANDARD = "STANDARD"  # ERROR, WARNING, INFO
    VERBOSE = "VERBOSE"    # Debug level for sections of code that are being edited
    DEBUG = "DEBUG"        # All levels including DEBUG

# Mapping of custom levels to logging levels
LEVEL_MAPPING: Dict[str, int] = {
    LogLevel.MINIMAL: logging.ERROR,
    LogLevel.BASIC: logging.WARNING,
    LogLevel.STANDARD: logging.INFO,
    LogLevel.VERBOSE: VERBOSE_LEVEL,
    LogLevel.DEBUG: logging.DEBUG
}

class CustomFormatter(logging.Formatter):
    """Custom formatter with different formats for different levels"""
    def __init__(self):
        super().__init__()
        # Detailed format for DEBUG, VERBOSE, and ERROR
        self.detailed_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        # Standard format for INFO
        self.standard_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        # Basic format for WARNING
        self.basic_fmt = '%(levelname)s - %(message)s'

    def format(self, record):
        # Choose format based on level
        if record.levelno in [logging.DEBUG, VERBOSE_LEVEL, logging.ERROR]:
            self.fmt = self.detailed_fmt
        elif record.levelno == logging.INFO:
            self.fmt = self.standard_fmt
        else:
            self.fmt = self.basic_fmt
        
        # Add timezone info
        if not hasattr(record, 'timezone'):
            tz = pytz.timezone('America/Los_Angeles')
            record.timezone = datetime.now(tz).strftime('%Z')
        
        return super().format(record)

def get_log_level(default: LogLevel = LogLevel.STANDARD) -> int:
    """Get log level from environment or use default"""
    env_level = os.getenv('LOG_LEVEL', default)
    try:
        # Try to parse as LogLevel enum
        level = LogLevel(env_level.upper())
        return LEVEL_MAPPING[level]
    except (ValueError, KeyError):
        # Fallback to default if invalid
        return LEVEL_MAPPING[default]

def setup_logging(name: str = __name__, log_level: Optional[int] = None) -> logging.Logger:
    """Set up logging with custom formatter and handlers
    
    Args:
        name: Logger name, defaults to module name
        log_level: Override environment log level if provided
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Use provided level or get from environment
    level = log_level if log_level is not None else get_log_level()
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)
    
    # Create file handler if LOG_DIR is set
    log_dir = os.getenv('LOG_DIR')
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(CustomFormatter())
        logger.addHandler(file_handler)
    
    # Add verbose method to logger
    def verbose(self, message, *args, **kwargs):
        self.log(VERBOSE_LEVEL, message, *args, **kwargs)
    
    logger.verbose = verbose.__get__(logger)
    return logger

# Create default logger
LOGGER = setup_logging() 