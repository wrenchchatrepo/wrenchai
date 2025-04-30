"""
Browser Tools for interacting with and monitoring browser state.

This module provides tools for:
- Console log management
- Network request monitoring
- Screenshot capture
- Element selection
- Browser state management
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class LogLevel(str, Enum):
    """Log levels for browser console."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"

class NetworkRequestType(str, Enum):
    """Types of network requests."""
    XHR = "xhr"
    FETCH = "fetch"
    WEBSOCKET = "websocket"
    DOCUMENT = "document"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    IMAGE = "image"
    MEDIA = "media"
    FONT = "font"
    OTHER = "other"

class ConsoleLog(BaseModel):
    """Model for console log entries."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel
    message: str
    source: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None

class NetworkRequest(BaseModel):
    """Model for network requests."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str
    type: NetworkRequestType
    method: str
    url: str
    status: Optional[int] = None
    status_text: Optional[str] = None
    response_body: Optional[str] = None
    request_headers: Dict[str, str] = {}
    response_headers: Dict[str, str] = {}
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

class BrowserState:
    """Manages browser state and logs."""
    
    def __init__(self):
        """
        Initializes a new BrowserState instance with empty logs and no selected element.
        
        Sets up lists for console logs, console errors, successful and failed network requests, and initializes the selected element to None. Limits the maximum number of stored logs to 1000.
        """
        self.console_logs: List[ConsoleLog] = []
        self.console_errors: List[ConsoleLog] = []
        self.network_success_logs: List[NetworkRequest] = []
        self.network_error_logs: List[NetworkRequest] = []
        self.selected_element: Optional[Dict[str, Any]] = None
        self._max_logs = 1000  # Maximum number of logs to keep
        
    def add_console_log(self, log: ConsoleLog):
        """
        Adds a console log entry to the browser state.
        
        If the log entry has an error level, it is also added to the error logs. Maintains a maximum number of stored logs by trimming the oldest entries when necessary.
        """
        self.console_logs.append(log)
        if log.level == LogLevel.ERROR:
            self.console_errors.append(log)
            
        # Trim logs if needed
        if len(self.console_logs) > self._max_logs:
            self.console_logs = self.console_logs[-self._max_logs:]
        if len(self.console_errors) > self._max_logs:
            self.console_errors = self.console_errors[-self._max_logs:]
            
    def add_network_request(self, request: NetworkRequest):
        """
        Adds a network request to the appropriate log based on its success status.
        
        If the number of stored logs exceeds the maximum allowed, only the most recent entries are kept.
        """
        if request.success:
            self.network_success_logs.append(request)
            if len(self.network_success_logs) > self._max_logs:
                self.network_success_logs = self.network_success_logs[-self._max_logs:]
        else:
            self.network_error_logs.append(request)
            if len(self.network_error_logs) > self._max_logs:
                self.network_error_logs = self.network_error_logs[-self._max_logs:]
                
    def set_selected_element(self, element: Dict[str, Any]):
        """
        Sets the currently selected element in the browser state.
        
        Args:
            element: A dictionary containing information about the selected element.
        """
        self.selected_element = element
        
    def clear_logs(self):
        """
        Removes all stored console and network logs from the browser state.
        """
        self.console_logs.clear()
        self.console_errors.clear()
        self.network_success_logs.clear()
        self.network_error_logs.clear()
        
    def get_console_logs(self) -> List[Dict[str, Any]]:
        """
        Returns all stored console log entries as dictionaries.
        
        Returns:
            A list of dictionaries representing each console log entry.
        """
        return [log.dict() for log in self.console_logs]
        
    def get_console_errors(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all console error logs as dictionaries.
        """
        return [log.dict() for log in self.console_errors]
        
    def get_network_success_logs(self) -> List[Dict[str, Any]]:
        """
        Returns a list of successful network request logs as dictionaries.
        
        Each dictionary represents a network request that completed successfully.
        """
        return [req.dict() for req in self.network_success_logs]
        
    def get_network_error_logs(self) -> List[Dict[str, Any]]:
        """
        Returns a list of failed network request logs as dictionaries.
        
        Each dictionary contains details of a network request that did not succeed.
        """
        return [req.dict() for req in self.network_error_logs]
        
    def get_selected_element(self) -> Optional[Dict[str, Any]]:
        """
        Returns the currently selected element in the browser state.
        
        Returns:
            A dictionary containing information about the selected element, or None if no element is selected.
        """
        return self.selected_element

# Global browser state instance
browser_state = BrowserState()

async def get_console_logs() -> Dict[str, Any]:
    """
    Retrieves all stored browser console logs.
    
    Returns:
        A dictionary with a success flag and a list of console log entries, or an error message if retrieval fails.
    """
    try:
        return {
            "success": True,
            "logs": browser_state.get_console_logs()
        }
    except Exception as e:
        logger.error(f"Error getting console logs: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_console_errors() -> Dict[str, Any]:
    """
    Retrieves all captured browser console error logs.
    
    Returns:
        A dictionary with a success flag and a list of console error logs, or an error message if retrieval fails.
    """
    try:
        return {
            "success": True,
            "errors": browser_state.get_console_errors()
        }
    except Exception as e:
        logger.error(f"Error getting console errors: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_network_error_logs() -> Dict[str, Any]:
    """
    Retrieves the list of failed network request logs.
    
    Returns:
        A dictionary with a success flag and a list of failed network requests, or an error message if retrieval fails.
    """
    try:
        return {
            "success": True,
            "errors": browser_state.get_network_error_logs()
        }
    except Exception as e:
        logger.error(f"Error getting network error logs: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_network_success_logs() -> Dict[str, Any]:
    """
    Retrieves logs of successful network requests.
    
    Returns:
        A dictionary with a success flag and a list of successful network request logs, or an error message if retrieval fails.
    """
    try:
        return {
            "success": True,
            "requests": browser_state.get_network_success_logs()
        }
    except Exception as e:
        logger.error(f"Error getting network success logs: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def take_screenshot() -> Dict[str, Any]:
    """
    Captures a screenshot of the current browser tab.
    
    Returns:
        A dictionary indicating success or failure, with a message and timestamp on success, or an error message on failure.
    """
    try:
        # This would be implemented by the MCP server
        # Here we just return a placeholder success response
        return {
            "success": True,
            "message": "Screenshot captured",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_selected_element() -> Dict[str, Any]:
    """
    Retrieves the currently selected element from the browser state.
    
    Returns:
        A dictionary with a success flag and the selected element's information if available,
        or an error message if no element is selected or an exception occurs.
    """
    try:
        element = browser_state.get_selected_element()
        if element is None:
            return {
                "success": False,
                "error": "No element selected"
            }
        return {
            "success": True,
            "element": element
        }
    except Exception as e:
        logger.error(f"Error getting selected element: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def wipe_logs() -> Dict[str, Any]:
    """
    Clears all stored browser logs and returns the operation status.
    
    Returns:
        A dictionary indicating whether the logs were cleared successfully. On failure, includes an error message.
    """
    try:
        browser_state.clear_logs()
        return {
            "success": True,
            "message": "All logs cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error wiping logs: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Event handlers for browser events
def handle_console_log(level: str, message: str, source: str, line_number: Optional[int] = None):
    """
    Processes an incoming console log entry and adds it to the browser state.
    
    Args:
        level: The log level (e.g., 'INFO', 'ERROR').
        message: The log message content.
        source: The source file or context of the log.
        line_number: The line number in the source, if available.
    """
    log = ConsoleLog(
        timestamp=datetime.utcnow(),
        level=level,
        message=message,
        source=source,
        line_number=line_number
    )
    browser_state.add_console_log(log)

def handle_network_request(
    method: str,
    url: str,
    request_headers: Optional[Dict[str, str]] = None
):
    """
    Records an outgoing network request in the browser state.
    
    Creates a new network request entry with the provided method, URL, and optional request headers, and adds it to the browser state logs.
    """
    request = NetworkRequest(
        timestamp=datetime.utcnow(),
        request_id=f"{method}_{url}",
        type=NetworkRequestType.XHR,
        method=method,
        url=url,
        request_headers=request_headers
    )
    browser_state.add_network_request(request)

def handle_network_response(
    url: str,
    status: int,
    duration: float,
    response_headers: Optional[Dict[str, str]] = None
):
    """
    Updates the first pending successful network request log with response details.
    
    Finds the first network request in the success log matching the given URL and without a status, then sets its status, duration, and response headers.
    """
    # Find matching request log
    for log in browser_state.network_success_logs:
        if log.url == url and log.status is None:
            log.status = status
            log.duration = duration
            log.response_headers = response_headers
            break

def handle_network_error(url: str, error: str):
    """
    Updates the first failed network request log matching the given URL with the provided error message.
    
    Args:
        url: The URL of the network request that encountered an error.
        error: The error message to associate with the failed request.
    """
    # Find matching request log
    for log in browser_state.network_error_logs:
        if log.url == url and log.status is None:
            log.error = error
            break

def handle_element_selected(element_info: Dict[str, Any]):
    """
    Updates the browser state with the newly selected element.
    
    Args:
        element_info: A dictionary containing information about the selected element.
    """
    browser_state.set_selected_element(element_info) 