"""
Logging Module for WrenchAI Streamlit Application.

This module provides utilities for configuring and managing application logging.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional, Union

from streamlit_app.utils.config_manager import LoggingConfig


def configure_logging(config: LoggingConfig) -> None:
    """
    Configure application logging based on provided configuration.
    
    Args:
        config: Logging configuration parameters
    """
    # Convert string level to logging level
    log_level = getattr(logging, config.level)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:  
        logger.removeHandler(handler)
    
    # Add console handler if enabled
    if config.console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(config.format))
        logger.addHandler(console_handler)
    
    # Add file handler
    if config.rotation:
        # Use rotating file handler
        file_handler = RotatingFileHandler(
            config.file,
            maxBytes=config.max_size * 1024 * 1024,  # Convert to bytes
            backupCount=config.backup_count
        )
    else:
        # Use standard file handler
        file_handler = logging.FileHandler(config.file)
    
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(config.format))
    logger.addHandler(file_handler)
    
    # Log configuration complete
    logger.info(f"Logging configured with level {config.level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name, typically __name__ of the module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, context: Dict = None) -> None:
    """
    Log a message with additional context information.
    
    Args:
        logger: Logger to use
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        context: Optional context dictionary with additional information
    """
    if context is None:
        context = {}
    
    # Add timestamp to context
    context['timestamp'] = datetime.now().isoformat()
    
    # Format message with context
    full_message = f"{message} | Context: {context}"
    
    # Log at appropriate level
    log_method = getattr(logger, level.lower())
    log_method(full_message)


def format_exception(exc: Exception) -> str:
    """
    Format an exception for logging.
    
    Args:
        exc: Exception to format
        
    Returns:
        str: Formatted exception string
    """
    return f"{type(exc).__name__}: {str(exc)}"


class StreamlitLogHandler(logging.Handler):
    """
    Custom log handler that displays logs in the Streamlit UI.
    
    This handler can be used to show log messages directly in the Streamlit
    interface, useful for debugging and monitoring.
    """
    
    def __init__(self, level=logging.INFO):
        """
        Initialize the handler.
        
        Args:
            level: Logging level
        """
        super().__init__(level)
        self.logs = []
        self.max_logs = 1000  # Maximum number of logs to keep
    
    def emit(self, record):
        """
        Emit a log record by adding it to the logs list.
        
        Args:
            record: Log record to emit
        """
        log_entry = self.format(record)
        self.logs.append({
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'formatted': log_entry
        })
        
        # Trim logs if they exceed the maximum
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
    
    def get_logs(self, level: Optional[str] = None, limit: int = 100) -> list:
        """
        Get logs, optionally filtered by level.
        
        Args:
            level: Optional log level filter
            limit: Maximum number of logs to return
            
        Returns:
            list: List of log entries
        """
        if level:
            filtered_logs = [log for log in self.logs if log['level'] == level.upper()]
        else:
            filtered_logs = self.logs
        
        return filtered_logs[-limit:]


# Create and configure a global Streamlit log handler that can be accessed from anywhere
streamlit_log_handler = StreamlitLogHandler()
streamlit_log_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)