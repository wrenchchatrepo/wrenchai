"""Base logger class providing common logging functionality.

This module implements a base logger class that can be extended by specific loggers
like SystemLogger, AgentLogger, etc. It provides:
- JSON formatted logging
- File rotation
- Console output
- Configurable log levels and handlers
- Structured logging with extra fields
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class LogConfig(BaseModel):
    """Configuration for logger settings."""
    
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None
    log_dir: str = "logs"
    max_bytes: int = 10_485_760  # 10MB
    backup_count: int = 5
    console_output: bool = True
    json_format: bool = True


class JSONFormatter(logging.Formatter):
    """Custom formatter for JSON log output."""
    
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


class BaseLogger:
    """Base logger class with common functionality."""

    def __init__(
        self,
        name: str,
        config: Optional[LogConfig] = None,
        log_type: str = "application",
        extra_handlers: Optional[List[logging.Handler]] = None
    ):
        """Initialize logger with configuration.
        
        Args:
            name: Logger name
            config: Logger configuration
            log_type: Type of logger (e.g., 'application', 'system', 'agent')
            extra_handlers: Additional logging handlers to add
        """
        self.name = name
        self.config = config or LogConfig()
        self.log_type = log_type
        self.logger = self._setup_logger(extra_handlers or [])

    def _setup_logger(self, extra_handlers: List[logging.Handler]) -> logging.Logger:
        """Set up logger with handlers and formatter."""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.config.log_level))

        # Prevent duplicate handlers
        logger.handlers = []

        handlers = []

        # Add file handler if log file is specified
        if self.config.log_file:
            log_path = Path(self.config.log_dir) / self.config.log_file
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count
            )
            handlers.append(file_handler)

        # Add console handler if enabled
        if self.config.console_output:
            console_handler = logging.StreamHandler()
            handlers.append(console_handler)

        # Add any extra handlers
        handlers.extend(extra_handlers)

        # Set formatter for all handlers
        formatter = (
            JSONFormatter() if self.config.json_format 
            else logging.Formatter(self.config.log_format)
        )

        for handler in handlers:
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _log(
        self,
        level: int,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[BaseException] = None,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """Log a message with the specified level and extra data."""
        extra = extra or {}
        extra.update({
            "log_type": self.log_type,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })
        
        if duration_ms is not None:
            extra["duration_ms"] = duration_ms

        self.logger.log(level, msg, extra={"extra": extra}, exc_info=exc_info)

    def debug(self, msg: str, **kwargs):
        """Log a debug message."""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """Log an info message."""
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """Log a warning message."""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, exc_info: Optional[BaseException] = None, **kwargs):
        """Log an error message."""
        self._log(logging.ERROR, msg, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, exc_info: Optional[BaseException] = None, **kwargs):
        """Log a critical message."""
        self._log(logging.CRITICAL, msg, exc_info=exc_info, **kwargs)

    def exception(self, msg: str, **kwargs):
        """Log an exception message."""
        self._log(logging.ERROR, msg, exc_info=True, **kwargs)

    def log_with_duration(
        self,
        level: int,
        msg: str,
        duration_ms: float,
        **kwargs
    ):
        """Log a message with execution duration."""
        self._log(level, msg, duration_ms=duration_ms, **kwargs) 