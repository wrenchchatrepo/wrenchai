"""
Structured logging configuration for WrenchAI.

This module provides a centralized logging setup with JSON formatting,
file and console output, and configurable log levels.
"""

import logging
import json
import os
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

@dataclass
class LoggerConfig:
    """Configuration for logger setup.
    
    Args:
        name: Logger name
        log_file: Path to log file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        log_level: Logging level
        format: Log message format
    """
    name: str
    log_file: str
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    log_level: int = logging.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class StructuredJsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage()
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_data)

def setup_logger(config: LoggerConfig) -> logging.Logger:
    """Set up logger with given configuration.
    
    Args:
        config: Logger configuration
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(config.name)
    logger.setLevel(config.log_level)
    
    # Create log directory if it doesn't exist
    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        config.log_file,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count
    )
    file_handler.setLevel(config.log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.log_level)
    
    # Create formatters
    json_formatter = StructuredJsonFormatter()
    text_formatter = logging.Formatter(config.format)
    
    # Add formatters to handlers
    file_handler.setFormatter(json_formatter)  # JSON for file
    console_handler.setFormatter(text_formatter)  # Text for console
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class BaseLogger:
    """Base logger class with common logging functionality."""
    
    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        log_level: int = logging.INFO
    ):
        """Initialize base logger.
        
        Args:
            name: Logger name
            log_file: Optional path to log file
            log_level: Logging level
        """
        config = LoggerConfig(
            name=name,
            log_file=log_file or f"logs/{name}/{name}.log",
            log_level=log_level
        )
        self.logger = setup_logger(config)
        
    def _format_extra(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format extra fields for logging.
        
        Args:
            extra: Additional fields to log
            
        Returns:
            Formatted extra fields
        """
        formatted = {"timestamp": datetime.utcnow().isoformat()}
        if extra:
            formatted.update(extra)
        return formatted
        
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message.
        
        Args:
            message: Log message
            extra: Additional fields to log
        """
        self.logger.info(message, extra=self._format_extra(extra))
        
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message.
        
        Args:
            message: Log message
            extra: Additional fields to log
        """
        self.logger.warning(message, extra=self._format_extra(extra))
        
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error message.
        
        Args:
            message: Log message
            extra: Additional fields to log
        """
        self.logger.error(message, extra=self._format_extra(extra))
        
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message.
        
        Args:
            message: Log message
            extra: Additional fields to log
        """
        self.logger.debug(message, extra=self._format_extra(extra))
        
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message.
        
        Args:
            message: Log message
            extra: Additional fields to log
        """
        self.logger.critical(message, extra=self._format_extra(extra))

# Default logger instance
default_config = LoggerConfig(
    name="wrenchai",
    level=logging.INFO,
    log_file="logs/wrenchai.log",
    console_output=True
)

logger = setup_logger(default_config) 