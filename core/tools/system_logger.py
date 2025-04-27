"""System logger implementation for monitoring system metrics and events.

This module implements a specialized logger for system-level monitoring, including:
- System metrics (CPU, memory, disk usage)
- Application events and errors
- Performance metrics
- Health checks
"""

import os
import psutil
import platform
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import threading
import time
import logging

from .base_logger import BaseLogger, LogConfig


class SystemMetrics:
    """System metrics collector."""

    @staticmethod
    def get_cpu_metrics() -> Dict[str, float]:
        """Get CPU usage metrics."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
        }

    @staticmethod
    def get_memory_metrics() -> Dict[str, float]:
        """Get memory usage metrics."""
        mem = psutil.virtual_memory()
        return {
            "total_memory": mem.total,
            "available_memory": mem.available,
            "memory_percent": mem.percent,
            "used_memory": mem.used,
        }

    @staticmethod
    def get_disk_metrics() -> Dict[str, Dict[str, float]]:
        """Get disk usage metrics."""
        disk_metrics = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_metrics[partition.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            except (PermissionError, OSError):
                continue
        return disk_metrics

    @staticmethod
    def get_network_metrics() -> Dict[str, Dict[str, int]]:
        """Get network I/O metrics."""
        net_io = psutil.net_io_counters()
        return {
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            }
        }

    @classmethod
    def get_all_metrics(cls) -> Dict[str, Dict]:
        """Get all system metrics."""
        return {
            "cpu": cls.get_cpu_metrics(),
            "memory": cls.get_memory_metrics(),
            "disk": cls.get_disk_metrics(),
            "network": cls.get_network_metrics(),
            "timestamp": datetime.utcnow().isoformat(),
        }


class SystemLogger(BaseLogger):
    """System logger for monitoring and metrics collection."""

    def __init__(
        self,
        name: str = "system",
        config: Optional[LogConfig] = None,
        metrics_interval: int = 60,  # seconds
    ):
        """Initialize system logger.
        
        Args:
            name: Logger name
            config: Logger configuration
            metrics_interval: Interval for collecting metrics in seconds
        """
        super().__init__(
            name=name,
            config=config,
            log_type="system"
        )
        self.metrics_interval = metrics_interval
        self.metrics = SystemMetrics()
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Initialize system info
        self.system_info = self._get_system_info()
        self.info("System logger initialized", extra=self.system_info)
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information.
        
        Returns:
            Dictionary containing system information
        """
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_partitions": [
                {
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype
                }
                for p in psutil.disk_partitions()
            ]
        }
    
    def _get_resource_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics.
        
        Returns:
            Dictionary containing resource metrics
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "per_cpu": psutil.cpu_percent(interval=1, percpu=True)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
    
    def _check_thresholds(self, metrics: Dict[str, Any]) -> List[Tuple[str, float, float]]:
        """Check if any metrics exceed their thresholds.
        
        Args:
            metrics: Dictionary of current metrics
            
        Returns:
            List of tuples containing (metric_name, current_value, threshold)
            for metrics that exceed their thresholds
        """
        exceeded = []
        
        # CPU threshold check
        if metrics["cpu"]["percent"] > self.config.cpu_threshold:
            exceeded.append(
                ("cpu_usage", metrics["cpu"]["percent"], self.config.cpu_threshold)
            )
        
        # Memory threshold check
        if metrics["memory"]["percent"] > self.config.memory_threshold:
            exceeded.append(
                ("memory_usage", metrics["memory"]["percent"], self.config.memory_threshold)
            )
        
        # Disk threshold check
        if metrics["disk"]["percent"] > self.config.disk_threshold:
            exceeded.append(
                ("disk_usage", metrics["disk"]["percent"], self.config.disk_threshold)
            )
        
        return exceeded
    
    def _monitor_resources(self) -> None:
        """Monitor system resources at regular intervals."""
        while not self._stop_monitoring.is_set():
            try:
                metrics = self._get_resource_metrics()
                exceeded_thresholds = self._check_thresholds(metrics)
                
                # Log regular metrics
                self.info("System metrics", extra=metrics)
                
                # Log threshold violations
                for metric, value, threshold in exceeded_thresholds:
                    self.warning(
                        f"{metric} exceeded threshold",
                        extra={
                            "metric": metric,
                            "current_value": value,
                            "threshold": threshold
                        }
                    )
                
                # Sleep for the monitoring interval
                self._stop_monitoring.wait(self.metrics_interval)
                
            except Exception as e:
                self.exception("Error in resource monitoring", extra={"error": str(e)})
                # Shorter sleep on error to retry sooner
                self._stop_monitoring.wait(min(self.metrics_interval, 15))
    
    def start_monitoring(self) -> None:
        """Start the resource monitoring thread."""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(
                target=self._monitor_resources,
                daemon=True
            )
            self._monitoring_thread.start()
            self.info("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the resource monitoring thread."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring.set()
            self._monitoring_thread.join()
            self.info("Resource monitoring stopped")
    
    def log_system_metrics(self):
        """Log current system metrics."""
        metrics = self.metrics.get_all_metrics()
        self.info("System metrics collected", extra={"metrics": metrics})

    def log_application_start(self):
        """Log application startup."""
        self.info(
            "Application started",
            extra={
                "pid": os.getpid(),
                "process": psutil.Process().name(),
                "working_directory": os.getcwd(),
            }
        )

    def log_application_stop(self):
        """Log application shutdown."""
        self.info(
            "Application stopped",
            extra={
                "pid": os.getpid(),
                "uptime": psutil.Process().create_time(),
            }
        )

    def log_error_event(
        self,
        error: Exception,
        context: Optional[Dict] = None
    ):
        """Log error event with context.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
        """
        self.error(
            f"Error occurred: {str(error)}",
            exc_info=error,
            extra={
                "error_type": type(error).__name__,
                "context": context or {},
            }
        )

    def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool,
        extra_data: Optional[Dict] = None
    ):
        """Log performance metric for an operation.
        
        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation succeeded
            extra_data: Additional data about the operation
        """
        self.info(
            f"Performance metric for {operation}",
            extra={
                "operation": operation,
                "duration_ms": duration_ms,
                "success": success,
                "data": extra_data or {},
            }
        )

    def log_health_check(self, checks: Dict[str, bool]):
        """Log health check results.
        
        Args:
            checks: Dictionary of check names and their status
        """
        all_healthy = all(checks.values())
        level = logging.INFO if all_healthy else logging.WARNING
        
        self.log(
            level,
            "Health check results",
            extra={
                "checks": checks,
                "all_healthy": all_healthy,
            }
        )

    def start_metrics_collection(self):
        """Start collecting system metrics at regular intervals."""
        def collect_metrics():
            while True:
                self.log_system_metrics()
                time.sleep(self.metrics_interval)

        thread = threading.Thread(
            target=collect_metrics,
            daemon=True,
            name="SystemMetricsCollector"
        )
        thread.start()

    def log_resource_usage(self, resource_type: str, usage: float):
        """Log specific resource usage.
        
        Args:
            resource_type: Type of resource (cpu, memory, disk, network)
            usage: Usage value
        """
        self.info(
            f"{resource_type.capitalize()} usage logged",
            extra={
                "resource_type": resource_type,
                "usage": usage,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ) 