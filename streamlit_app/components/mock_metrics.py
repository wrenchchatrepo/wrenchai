"""Mock data provider for metrics dashboard.

Provides simulated metrics data for testing the dashboard.
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any


def generate_mock_system_metrics() -> Dict[str, Any]:
    """Generate mock system metrics."""
    return {
        "cpu_usage": random.uniform(5, 85),
        "memory_usage": random.uniform(20, 75),
        "disk_usage": random.uniform(30, 90),
        "network_traffic": random.uniform(10, 100),
        "db_connections": random.randint(1, 50),
        "cache_hit_rate": random.uniform(0.6, 0.95),
        "timestamp": datetime.now().isoformat()
    }


def generate_mock_agent_metrics() -> Dict[str, List[Dict[str, Any]]]:
    """Generate mock agent performance metrics."""
    agent_names = ["SuperAgent", "InspectorAgent", "JourneyAgent", "DocAgent"]
    metrics = {}
    
    for agent in agent_names:
        # Generate a time series of metrics for each agent
        now = datetime.now()
        data = []
        
        # Start with a base value for consistency in trends
        base_tasks = random.randint(50, 200)
        base_success_rate = random.uniform(0.7, 0.98)
        
        for i in range(24):  # 24 hourly data points
            timestamp = (now - timedelta(hours=24-i)).isoformat()
            
            # Add some randomness but maintain a trend
            tasks_delta = random.randint(-5, 10)
            success_delta = random.uniform(-0.05, 0.05)
            
            # Calculate current values
            tasks_completed = max(0, base_tasks + i * 5 + tasks_delta)
            success_rate = max(0, min(1, base_success_rate + i * 0.005 + success_delta))
            
            data.append({
                "timestamp": timestamp,
                "tasks_completed": tasks_completed,
                "tasks_failed": int(tasks_completed * (1 - success_rate)),
                "success_rate": success_rate,
                "active": random.random() > 0.1  # 90% chance of being active
            })
        
        metrics[agent] = data
    
    return metrics


def generate_mock_api_metrics() -> Dict[str, Any]:
    """Generate mock API performance metrics."""
    # Generate mock response times
    response_times = []
    for _ in range(100):
        response_times.append({
            "endpoint": random.choice(["/api/agents", "/api/tasks", "/api/status", "/api/playbooks"]),
            "method": random.choice(["GET", "POST", "PUT"]),
            "duration": random.lognormvariate(3, 0.7),  # log-normal distribution for response times
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 60))).isoformat()
        })
    
    # Generate mock errors
    error_types = ["Timeout", "Authentication", "Validation", "Server Error", "Not Found"]
    error_counts = {error: random.randint(1, 30) for error in error_types}
    
    errors = []
    for error_type, count in error_counts.items():
        errors.append({
            "type": error_type,
            "count": count
        })
    
    return {
        "total_requests": random.randint(1000, 5000),
        "avg_response_time": random.uniform(50, 200),
        "error_rate": random.uniform(0.01, 0.1),
        "active_users": random.randint(10, 100),
        "response_times": response_times,
        "errors": errors
    }


class MockRedisClient:
    """Mock Redis client for simulating Redis functionality."""
    
    def __init__(self):
        """Initialize the mock client with some data."""
        self.data = {}
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """Initialize with mock metrics data."""
        self.data["system_metrics"] = json.dumps(generate_mock_system_metrics())
        self.data["agent_metrics"] = json.dumps(generate_mock_agent_metrics())
        self.data["api_metrics"] = json.dumps(generate_mock_api_metrics())
    
    def get(self, key):
        """Get a value from the mock Redis store."""
        # Refresh system metrics each time to simulate real-time changes
        if key == "system_metrics":
            self.data[key] = json.dumps(generate_mock_system_metrics())
        
        # Return the data if it exists
        return self.data.get(key)
    
    def from_url(self, url):
        """Mock the from_url method to return self."""
        return self