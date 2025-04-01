"""Logging configuration and setup.

Provides consistent logging configuration across the application,
including file and console handlers with appropriate formatting.
"""
import os
import sys

from pathlib import Path
import logging
from typing import Dict, Any, Tuple


sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.config.configuration  import Configuration


def setup_logging(config: Configuration) -> Tuple[logging.FileHandler, logging.StreamHandler]:
    """
    Setup and return logging handlers.

    Args:
    config: Configuration object with debug_level setting

    Returns:
    tuple: (file_handler, console_handler) configured logging handlers
    """
    try:
        # Create log directory and file path
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "agent_debug.log"

        # Setup formatter with additional context for node and error tracking
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(node_type)s - %(error_context)s - %(message)s',
            defaults={
                'node_type': 'general',
                'error_context': ''
            }
        )

        # Create file handler - level from config
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(getattr(logging, config.file_level))
        file_handler.setFormatter(formatter)

        # Create console handler - level from config
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.console_level))
        console_handler.setFormatter(formatter)

        # Define formatters for different log levels
        info_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
        )
        error_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(node_type)s - %(error_context)s - %(message)s',
            defaults={
                'node_type': 'general',
                'error_context': ''
            }
        )
        debug_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - DEBUG - %(message)s'
        )

        # Set root logger to most verbose level from config
        root_level = min(
            getattr(logging, config.file_level),
            getattr(logging, config.console_level)
        )
        root_logger = logging.getLogger()
        root_logger.setLevel(root_level)

        return file_handler, console_handler

    except Exception as e:
        # Fallback logging setup in case of configuration error
        error_context = {
            "error_type": type(e).__name__,
            "error_details": str(e),
            "operation": "setup_logging"
        }

        # Create basic handlers with error formatting
        basic_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - ERROR - %(message)s'
        )

        fallback_file = logging.FileHandler("logs/error.log", mode='a')
        fallback_file.setFormatter(basic_formatter)

        fallback_console = logging.StreamHandler()
        fallback_console.setFormatter(basic_formatter)

        # Log the error
        logging.error(f"Logging setup failed: {error_context}")

        return fallback_file, fallback_console