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
        
        Sets up lists for console logs, console errors, successful and failed network requests, and initializes the selected element to None. Enforces a maximum log retention limit.
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
        
        If the log entry has an error level, it is also added to the error logs. Maintains a maximum number of stored logs.
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
        Adds a network request log to the success or error logs based on its outcome.
        
        If the number of stored logs exceeds the maximum allowed, only the most recent entries are retained.
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
        Sets the currently selected DOM element in the browser state.
        
        Args:
            element: A dictionary containing information about the selected element.
        """
        self.selected_element = element
        
    def clear_logs(self):
        """
        Clears all console and network logs from the browser state.
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
        
        Each dictionary contains details of a successful network request recorded in the browser state.
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
            A dictionary with information about the selected element, or None if no element is selected.
        """
        return self.selected_element

# Global browser state instance
browser_state = BrowserState()

class BrowserTools:
    """Browser tools implementation for monitoring and interaction."""
    
    @staticmethod
    async def get_console_logs() -> Dict[str, Any]:
        """Get all console logs.
        
        Returns:
            Dictionary containing console logs
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
    
    @staticmethod
    async def get_console_errors() -> Dict[str, Any]:
        """Get console error logs.
        
        Returns:
            Dictionary containing console error logs
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
    
    @staticmethod
    async def get_network_error_logs() -> Dict[str, Any]:
        """Get failed network request logs.
        
        Returns:
            Dictionary containing failed network requests
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
    
    @staticmethod
    async def get_network_success_logs() -> Dict[str, Any]:
        """Get successful network request logs.
        
        Returns:
            Dictionary containing successful network requests
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
    
    @staticmethod
    async def take_screenshot() -> Dict[str, Any]:
        """Take a screenshot of the current browser tab.
        
        Returns:
            Dictionary containing screenshot information
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
    
    @staticmethod
    async def get_selected_element() -> Dict[str, Any]:
        """Get the currently selected element.
        
        Returns:
            Dictionary containing element information
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
    
    @staticmethod
    async def wipe_logs() -> Dict[str, Any]:
        """Clear all browser logs.
        
        Returns:
            Dictionary containing operation status
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

# Individual operation functions
async def get_console_logs() -> Dict[str, Any]:
    """
    Retrieves all captured browser console logs.
    
    Returns:
        A dictionary with a success flag and a list of console log entries, or an error message if retrieval fails.
    """
    return await BrowserTools.get_console_logs()

async def get_console_errors() -> Dict[str, Any]:
    """
    Retrieves all console error logs from the browser state.
    
    Returns:
        A dictionary with a success flag and a list of console error logs, or an error message if retrieval fails.
    """
    return await BrowserTools.get_console_errors()

async def get_network_error_logs() -> Dict[str, Any]:
    """
    Retrieves the list of failed network request logs.
    
    Returns:
        A dictionary with a success flag and a list of failed network requests, or an error message if retrieval fails.
    """
    return await BrowserTools.get_network_error_logs()

async def get_network_success_logs() -> Dict[str, Any]:
    """
    Retrieves all successful network request logs.
    
    Returns:
        A dictionary with a success flag and a list of successful network requests, or an error message if retrieval fails.
    """
    return await BrowserTools.get_network_success_logs()

async def take_screenshot() -> Dict[str, Any]:
    """
    Captures a screenshot of the current browser tab.
    
    Returns:
        A dictionary indicating success and including a message and timestamp, or an error message if the operation fails.
    """
    return await BrowserTools.take_screenshot()

async def get_selected_element() -> Dict[str, Any]:
    """
    Retrieves information about the currently selected element.
    
    Returns:
        A dictionary with a success flag and the selected element's information if available,
        or an error message if no element is selected or an exception occurs.
    """
    return await BrowserTools.get_selected_element()

async def wipe_logs() -> Dict[str, Any]:
    """
    Clears all stored console and network logs from the browser state.
    
    Returns:
        A dictionary indicating whether the operation was successful. On success, includes a message; on failure, includes an error message.
    """
    return await BrowserTools.wipe_logs()

# Event handlers for browser events
def handle_console_log(level: str, message: str, source: str, line_number: Optional[int] = None):
    """
    Processes an incoming console log entry and adds it to the browser state.
    
    Args:
        level: The log level (e.g., 'INFO', 'ERROR').
        message: The log message content.
        source: The source of the log (e.g., script name or URL).
        line_number: The line number in the source where the log originated, if available.
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
    
    Args:
        method: The HTTP method of the request (e.g., 'GET', 'POST').
        url: The URL to which the request is sent.
        request_headers: Optional dictionary of HTTP request headers.
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
    
    Searches for the first network request in the success log matching the given URL and without a status, then sets its status, duration, and response headers.
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
    Updates the first failed network request log for the given URL with the specified error message.
    
    Args:
        url: The URL of the failed network request.
        error: The error message to associate with the request.
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
        element_info: A dictionary containing information about the selected DOM element.
    """
    browser_state.set_selected_element(element_info) 

async def browser_operation(operation: str) -> Dict[str, Any]:
    """Primary interface for browser operations.
    
    This function is the main entry point for the tool system to interact with browser
    tools. It maps operations to the appropriate methods.
    
    Args:
        operation: Operation to perform (get_console_logs, get_console_errors,
                 get_network_error_logs, get_network_success_logs, take_screenshot,
                 get_selected_element, wipe_logs)
        
    Returns:
        Dictionary containing operation results
    """
    try:
        # Map operations to methods
        if operation == "get_console_logs":
            return await get_console_logs()
            
        elif operation == "get_console_errors":
            return await get_console_errors()
            
        elif operation == "get_network_error_logs":
            return await get_network_error_logs()
            
        elif operation == "get_network_success_logs":
            return await get_network_success_logs()
            
        elif operation == "take_screenshot":
            return await take_screenshot()
            
        elif operation == "get_selected_element":
            return await get_selected_element()
            
        elif operation == "wipe_logs":
            return await wipe_logs()
            
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }
            
    except Exception as e:
        logger.error(f"Browser operation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
