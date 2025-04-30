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
        """Initialize browser state."""
        self.console_logs: List[ConsoleLog] = []
        self.console_errors: List[ConsoleLog] = []
        self.network_success_logs: List[NetworkRequest] = []
        self.network_error_logs: List[NetworkRequest] = []
        self.selected_element: Optional[Dict[str, Any]] = None
        self._max_logs = 1000  # Maximum number of logs to keep
        
    def add_console_log(self, log: ConsoleLog):
        """Add a console log entry.
        
        Args:
            log: Console log entry to add
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
        """Add a network request log.
        
        Args:
            request: Network request to add
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
        """Set the currently selected element.
        
        Args:
            element: Element information
        """
        self.selected_element = element
        
    def clear_logs(self):
        """Clear all logs."""
        self.console_logs.clear()
        self.console_errors.clear()
        self.network_success_logs.clear()
        self.network_error_logs.clear()
        
    def get_console_logs(self) -> List[Dict[str, Any]]:
        """Get all console logs.
        
        Returns:
            List of console logs
        """
        return [log.dict() for log in self.console_logs]
        
    def get_console_errors(self) -> List[Dict[str, Any]]:
        """Get console error logs.
        
        Returns:
            List of console error logs
        """
        return [log.dict() for log in self.console_errors]
        
    def get_network_success_logs(self) -> List[Dict[str, Any]]:
        """Get successful network request logs.
        
        Returns:
            List of successful network requests
        """
        return [req.dict() for req in self.network_success_logs]
        
    def get_network_error_logs(self) -> List[Dict[str, Any]]:
        """Get failed network request logs.
        
        Returns:
            List of failed network requests
        """
        return [req.dict() for req in self.network_error_logs]
        
    def get_selected_element(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected element.
        
        Returns:
            Selected element information or None
        """
        return self.selected_element

# Global browser state instance
browser_state = BrowserState()

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

# Event handlers for browser events
def handle_console_log(level: str, message: str, source: str, line_number: Optional[int] = None):
    """Handle incoming console log."""
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
    """Handle outgoing network request."""
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
    """Handle incoming network response."""
    # Find matching request log
    for log in browser_state.network_success_logs:
        if log.url == url and log.status is None:
            log.status = status
            log.duration = duration
            log.response_headers = response_headers
            break

def handle_network_error(url: str, error: str):
    """Handle network request error."""
    # Find matching request log
    for log in browser_state.network_error_logs:
        if log.url == url and log.status is None:
            log.error = error
            break

def handle_element_selected(element_info: Dict[str, Any]):
    """Handle element selection."""
    browser_state.set_selected_element(element_info) 