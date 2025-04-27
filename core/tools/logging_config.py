"""Logging configuration module."""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import os

@dataclass
class LoggingConfig:
    """Configuration for logging system."""
    
    # Base logging directory
    log_dir: str = "logs"
    
    # Log file paths
    system_log_file: str = "system/metrics.log"
    app_log_file: str = "app/application.log"
    access_log_file: str = "access/api.log"
    error_log_file: str = "error/error.log"
    
    # Log rotation settings
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # Log levels
    system_log_level: int = 20  # INFO
    app_log_level: int = 20  # INFO
    access_log_level: int = 20  # INFO
    error_log_level: int = 40  # ERROR
    
    # Resource monitoring thresholds
    cpu_threshold: float = 80.0  # 80%
    memory_threshold: float = 90.0  # 90%
    disk_threshold: float = 85.0  # 85%
    
    # Monitoring intervals (seconds)
    system_metrics_interval: int = 60
    process_metrics_interval: int = 30
    
    def __post_init__(self):
        """Create log directories if they don't exist."""
        self._create_log_dirs()
    
    def _create_log_dirs(self) -> None:
        """Create necessary log directories."""
        base_dir = Path(self.log_dir)
        dirs = ["system", "app", "access", "error"]
        
        for dir_name in dirs:
            dir_path = base_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_file_path(self, log_type: str) -> str:
        """Get full path for log file.
        
        Args:
            log_type: Type of log file (system, app, access, error)
            
        Returns:
            Full path to log file
        """
        return str(Path(self.log_dir) / getattr(self, f"{log_type}_log_file"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.
        
        Returns:
            Dictionary of configuration values
        """
        return {
            "log_dir": self.log_dir,
            "files": {
                "system": self.get_file_path("system"),
                "app": self.get_file_path("app"),
                "access": self.get_file_path("access"),
                "error": self.get_file_path("error")
            },
            "rotation": {
                "max_bytes": self.max_bytes,
                "backup_count": self.backup_count
            },
            "levels": {
                "system": self.system_log_level,
                "app": self.app_log_level,
                "access": self.access_log_level,
                "error": self.error_log_level
            },
            "thresholds": {
                "cpu": self.cpu_threshold,
                "memory": self.memory_threshold,
                "disk": self.disk_threshold
            },
            "intervals": {
                "system_metrics": self.system_metrics_interval,
                "process_metrics": self.process_metrics_interval
            }
        }

class LoggingConfigFactory:
    """Factory for creating environment-specific logging configurations."""
    
    @staticmethod
    def create_config(env: str = None) -> LoggingConfig:
        """Create logging configuration for specified environment.
        
        Args:
            env: Environment name (development, staging, production)
            
        Returns:
            LoggingConfig instance
        """
        env = env or os.getenv("APP_ENV", "development")
        
        if env == "production":
            return LoggingConfig(
                log_dir="/var/log/wrenchai",
                max_bytes=50 * 1024 * 1024,  # 50MB
                backup_count=10,
                system_log_level=20,  # INFO
                app_log_level=20,  # INFO
                access_log_level=20,  # INFO
                error_log_level=40,  # ERROR
                cpu_threshold=75.0,
                memory_threshold=85.0,
                disk_threshold=80.0,
                system_metrics_interval=30,
                process_metrics_interval=15
            )
        
        elif env == "staging":
            return LoggingConfig(
                log_dir="logs",
                max_bytes=20 * 1024 * 1024,  # 20MB
                backup_count=7,
                system_log_level=20,  # INFO
                app_log_level=20,  # INFO
                access_log_level=20,  # INFO
                error_log_level=40,  # ERROR
                cpu_threshold=80.0,
                memory_threshold=90.0,
                disk_threshold=85.0,
                system_metrics_interval=45,
                process_metrics_interval=20
            )
        
        else:  # development
            return LoggingConfig(
                log_dir="logs",
                max_bytes=10 * 1024 * 1024,  # 10MB
                backup_count=5,
                system_log_level=10,  # DEBUG
                app_log_level=10,  # DEBUG
                access_log_level=10,  # DEBUG
                error_log_level=40,  # ERROR
                cpu_threshold=90.0,
                memory_threshold=95.0,
                disk_threshold=90.0,
                system_metrics_interval=60,
                process_metrics_interval=30
            )

def setup_logging(env: Optional[str] = None) -> LoggingConfig:
    """Set up logging configuration.
    
    Args:
        env: Optional environment name
        
    Returns:
        LoggingConfig instance
    """
    config = LoggingConfigFactory.create_config(env)
    config._create_log_dirs()
    return config 