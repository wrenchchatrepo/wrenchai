from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import psutil
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Summary
import threading
import queue
import logging
import json
import os
from dataclasses import dataclass
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings
import time
import socket
from collections import deque

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(str, Enum):
    """Enumeration for alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(str, Enum):
    """Enumeration for metric types"""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class MetricConfig(BaseModel):
    """Configuration for a monitoring metric"""
    name: str = Field(..., description="Name of the metric")
    description: str = Field(..., description="Description of the metric")
    query: Optional[str] = Field(default=None, description="SQL query for database metrics")
    interval: int = Field(default=60, description="Collection interval in seconds")
    metric_type: MetricType = Field(default=MetricType.GAUGE, description="Type of metric")
    threshold: Optional[float] = Field(default=None, description="Alert threshold")
    alert_message: Optional[str] = Field(default=None, description="Alert message template")
    alert_severity: AlertSeverity = Field(default=AlertSeverity.WARNING, description="Alert severity level")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")
    buckets: Optional[List[float]] = Field(default=None, description="Histogram buckets")
    aggregation_window: Optional[int] = Field(default=None, description="Window size for aggregation in seconds")

class MetricData(BaseModel):
    """Model for collected metric data"""
    timestamp: datetime = Field(..., description="Timestamp of the metric")
    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Metric value")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class Alert(BaseModel):
    """Model for monitoring alerts"""
    timestamp: datetime = Field(..., description="Timestamp of the alert")
    metric_name: str = Field(..., description="Name of the metric that triggered the alert")
    message: str = Field(..., description="Alert message")
    value: float = Field(..., description="Value that triggered the alert")
    threshold: float = Field(..., description="Threshold that was exceeded")
    severity: AlertSeverity = Field(..., description="Severity level of the alert")
    labels: Dict[str, str] = Field(default_factory=dict, description="Alert labels")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

@dataclass
class MetricState:
    """Internal state for metric collection"""
    config: MetricConfig
    prometheus_metric: Union[Gauge, Counter, Histogram, Summary]
    last_value: Optional[float] = None
    last_update: Optional[datetime] = None
    values_buffer: deque = None

class MonitoringTool:
    """Tool for database and system monitoring"""
    
    def __init__(self):
        self.database_url: Optional[str] = None
        self.metrics: Dict[str, MetricState] = {}
        self.alerts: List[Alert] = []
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_collection = threading.Event()
        self._metrics_queue = queue.Queue()
        self._alert_handlers: List[callable] = []
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._data_retention_days = 30
        
    def configure_database(self, connection_string: str) -> bool:
        """Configure the database connection"""
        try:
            self.database_url = connection_string
            return True
        except Exception as e:
            logger.error(f"Error configuring database: {str(e)}")
            return False
            
    def add_metric(self, config: MetricConfig) -> bool:
        """Add a new metric to monitor"""
        try:
            # Create Prometheus metric
            if config.metric_type == MetricType.GAUGE:
                prom_metric = Gauge(config.name, config.description, labelnames=list(config.labels.keys()))
            elif config.metric_type == MetricType.COUNTER:
                prom_metric = Counter(config.name, config.description, labelnames=list(config.labels.keys()))
            elif config.metric_type == MetricType.HISTOGRAM:
                prom_metric = Histogram(config.name, config.description, labelnames=list(config.labels.keys()),
                                      buckets=config.buckets or Histogram.DEFAULT_BUCKETS)
            else:  # SUMMARY
                prom_metric = Summary(config.name, config.description, labelnames=list(config.labels.keys()))
                
            # Initialize metric state
            state = MetricState(
                config=config,
                prometheus_metric=prom_metric,
                values_buffer=deque(maxlen=1000) if config.aggregation_window else None
            )
            
            self.metrics[config.name] = state
            return True
        except Exception as e:
            logger.error(f"Error adding metric {config.name}: {str(e)}")
            return False
            
    def start_collection(self, prometheus_port: int = 9090):
        """Start metric collection in a background thread"""
        if self._collection_thread and self._collection_thread.is_alive():
            logger.warning("Metric collection already running")
            return
            
        # Start Prometheus HTTP server
        try:
            start_http_server(prometheus_port)
            logger.info(f"Started Prometheus metrics server on port {prometheus_port}")
        except Exception as e:
            logger.error(f"Error starting Prometheus server: {str(e)}")
            return
            
        self._stop_collection.clear()
        self._collection_thread = threading.Thread(target=self._collection_loop)
        self._collection_thread.daemon = True
        self._collection_thread.start()
        
    def stop_collection(self):
        """Stop metric collection"""
        if self._collection_thread:
            self._stop_collection.set()
            self._collection_thread.join()
            self._collection_thread = None
            
    def _collection_loop(self):
        """Main metric collection loop"""
        while not self._stop_collection.is_set():
            current_time = datetime.now()
            
            # Collect metrics in parallel
            futures = []
            for metric_name, state in self.metrics.items():
                if (not state.last_update or
                    (current_time - state.last_update).total_seconds() >= state.config.interval):
                    futures.append(self._executor.submit(self._collect_metric, metric_name))
                    
            # Wait for all collections to complete
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error collecting metric: {str(e)}")
                    
            # Process queued metrics
            self._process_metrics_queue()
            
            # Clean up old data
            self._cleanup_old_data()
            
            # Sleep until next collection
            time.sleep(1)
            
    def _collect_metric(self, metric_name: str):
        """Collect a single metric"""
        state = self.metrics[metric_name]
        try:
            # Get metric value
            if state.config.query:
                value = self._collect_database_metric(state.config.query)
            else:
                value = self._collect_system_metric(metric_name)
                
            # Update metric state
            timestamp = datetime.now()
            metric_data = MetricData(
                timestamp=timestamp,
                metric_name=metric_name,
                value=value,
                labels=state.config.labels
            )
            
            # Queue metric for processing
            self._metrics_queue.put(metric_data)
            
        except Exception as e:
            logger.error(f"Error collecting metric {metric_name}: {str(e)}")
            
    def _collect_database_metric(self, query: str) -> float:
        """Collect a metric from the database"""
        if not self.database_url:
            raise ValueError("Database not configured")
            
        import sqlalchemy as sa
        engine = sa.create_engine(self.database_url)
        with engine.connect() as conn:
            result = conn.execute(sa.text(query))
            row = result.fetchone()
            if row:
                return float(row[0])
            raise ValueError("Query returned no results")
            
    def _collect_system_metric(self, metric_name: str) -> float:
        """Collect a system metric"""
        if metric_name == "cpu_percent":
            return psutil.cpu_percent()
        elif metric_name == "memory_percent":
            return psutil.virtual_memory().percent
        elif metric_name == "disk_usage_percent":
            return psutil.disk_usage("/").percent
        elif metric_name == "network_io_bytes_sent":
            return psutil.net_io_counters().bytes_sent
        elif metric_name == "network_io_bytes_recv":
            return psutil.net_io_counters().bytes_recv
        else:
            raise ValueError(f"Unknown system metric: {metric_name}")
            
    def _process_metrics_queue(self):
        """Process queued metrics"""
        while not self._metrics_queue.empty():
            try:
                metric_data = self._metrics_queue.get_nowait()
                state = self.metrics[metric_data.metric_name]
                
                # Update Prometheus metric
                if state.config.metric_type == MetricType.COUNTER:
                    if state.last_value is not None:
                        increment = max(0, metric_data.value - state.last_value)
                        state.prometheus_metric.inc(increment)
                else:
                    state.prometheus_metric.labels(**metric_data.labels).set(metric_data.value)
                    
                # Update metric state
                state.last_value = metric_data.value
                state.last_update = metric_data.timestamp
                
                # Add to buffer if aggregation is enabled
                if state.values_buffer is not None:
                    state.values_buffer.append((metric_data.timestamp, metric_data.value))
                    
                # Check threshold
                self._check_threshold(metric_data)
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing metric: {str(e)}")
                
    def _check_threshold(self, metric_data: MetricData):
        """Check if a metric has exceeded its threshold"""
        state = self.metrics[metric_data.metric_name]
        if state.config.threshold is not None:
            if metric_data.value > state.config.threshold:
                alert = Alert(
                    timestamp=metric_data.timestamp,
                    metric_name=metric_data.metric_name,
                    message=state.config.alert_message or f"Metric {metric_data.metric_name} exceeded threshold",
                    value=metric_data.value,
                    threshold=state.config.threshold,
                    severity=state.config.alert_severity,
                    labels=metric_data.labels,
                    metadata=metric_data.metadata
                )
                self.alerts.append(alert)
                self._handle_alert(alert)
                
    def _handle_alert(self, alert: Alert):
        """Handle a new alert"""
        logger.warning(f"Alert: {alert.message} (value: {alert.value}, threshold: {alert.threshold})")
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {str(e)}")
                
    def add_alert_handler(self, handler: callable):
        """Add a new alert handler"""
        self._alert_handlers.append(handler)
        
    def get_alerts(self, severity: Optional[AlertSeverity] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[Alert]:
        """Get filtered alerts"""
        filtered = self.alerts
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
            
        if start_time:
            filtered = [a for a in filtered if a.timestamp >= start_time]
            
        if end_time:
            filtered = [a for a in filtered if a.timestamp <= end_time]
            
        return filtered
        
    def get_metric_data(self, metric_name: str,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> pd.DataFrame:
        """Get historical metric data"""
        state = self.metrics.get(metric_name)
        if not state or not state.values_buffer:
            return pd.DataFrame()
            
        # Convert buffer to DataFrame
        df = pd.DataFrame(list(state.values_buffer), columns=["timestamp", "value"])
        
        # Apply time filters
        if start_time:
            df = df[df["timestamp"] >= start_time]
        if end_time:
            df = df[df["timestamp"] <= end_time]
            
        return df
        
    def generate_report(self, format: str = "html") -> str:
        """Generate a monitoring report"""
        # Create subplots for each metric
        fig = make_subplots(rows=len(self.metrics), cols=1,
                           subplot_titles=[m.config.description for m in self.metrics.values()])
        
        # Add metric plots
        for i, (metric_name, state) in enumerate(self.metrics.items(), 1):
            if state.values_buffer:
                df = pd.DataFrame(list(state.values_buffer), columns=["timestamp", "value"])
                trace = go.Scatter(x=df["timestamp"], y=df["value"], name=metric_name)
                fig.add_trace(trace, row=i, col=1)
                
                if state.config.threshold is not None:
                    fig.add_hline(y=state.config.threshold, line_dash="dash",
                                line_color="red", row=i, col=1)
                    
        # Update layout
        fig.update_layout(height=300 * len(self.metrics), showlegend=True,
                         title_text="Monitoring Report")
        
        if format == "html":
            return fig.to_html()
        else:  # json
            return fig.to_json()
            
    def export_metrics(self, format: str = "csv", filepath: Optional[str] = None) -> Optional[str]:
        """Export collected metrics"""
        # Prepare data
        data = []
        for metric_name, state in self.metrics.items():
            if state.values_buffer:
                for timestamp, value in state.values_buffer:
                    data.append({
                        "metric_name": metric_name,
                        "timestamp": timestamp,
                        "value": value,
                        **state.config.labels
                    })
                    
        if not data:
            return None
            
        df = pd.DataFrame(data)
        
        if format == "csv":
            if filepath:
                df.to_csv(filepath, index=False)
                return filepath
            else:
                return df.to_csv(index=False)
        else:  # json
            if filepath:
                df.to_json(filepath, orient="records")
                return filepath
            else:
                return df.to_json(orient="records")
                
    def _cleanup_old_data(self):
        """Clean up data older than retention period"""
        cutoff = datetime.now() - timedelta(days=self._data_retention_days)
        
        # Clean up alerts
        self.alerts = [a for a in self.alerts if a.timestamp >= cutoff]
        
        # Clean up metric buffers
        for state in self.metrics.values():
            if state.values_buffer:
                while (state.values_buffer and
                       state.values_buffer[0][0] < cutoff):
                    state.values_buffer.popleft()
                    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system metrics"""
        metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage("/").percent,
            "network_io_bytes_sent": psutil.net_io_counters().bytes_sent,
            "network_io_bytes_recv": psutil.net_io_counters().bytes_recv
        }
        
        # Add per-CPU metrics
        cpu_times = psutil.cpu_times_percent(percpu=True)
        for i, cpu in enumerate(cpu_times):
            metrics[f"cpu_{i}_user"] = cpu.user
            metrics[f"cpu_{i}_system"] = cpu.system
            
        # Add memory details
        mem = psutil.virtual_memory()
        metrics.update({
            "memory_total": mem.total,
            "memory_available": mem.available,
            "memory_used": mem.used,
            "memory_free": mem.free
        })
        
        # Add disk IO stats
        disk_io = psutil.disk_io_counters()
        if disk_io:
            metrics.update({
                "disk_read_bytes": disk_io.read_bytes,
                "disk_write_bytes": disk_io.write_bytes,
                "disk_read_count": disk_io.read_count,
                "disk_write_count": disk_io.write_count
            })
            
        return metrics
        
    def clear_old_data(self, days: int = 30):
        """Clear metric data and alerts older than specified days"""
        self._data_retention_days = days
        self._cleanup_old_data() 