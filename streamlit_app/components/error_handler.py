"""Error handling component for Streamlit-FastAPI integration."""

import streamlit as st
from typing import Optional, Dict, Any, Callable
import httpx
from websockets.exceptions import WebSocketException
import asyncio
import functools
import time
from datetime import datetime

class APIError(Exception):
    """Custom API error."""
    def __init__(self, message: str, status_code: int = None, details: Dict = None):
        """
        Initializes an APIError with a message, optional status code, and additional details.
        
        Args:
            message: Description of the API error.
            status_code: Optional HTTP status code associated with the error.
            details: Optional dictionary with additional error information.
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ErrorHandler:
    """Handles API and WebSocket errors in Streamlit."""
    
    def __init__(self):
        """
        Initializes the error handler state.
        
        Sets the error count to zero, clears the last error timestamp, and sets the initial backoff time to one second.
        """
        self.error_count = 0
        self.last_error_time = None
        self.backoff_time = 1  # Initial backoff time in seconds
        
    def reset(self):
        """
        Resets the error tracking state for the error handler.
        
        Sets the error count, last error time, and backoff time to their initial values.
        """
        self.error_count = 0
        self.last_error_time = None
        self.backoff_time = 1
        
    def should_retry(self) -> bool:
        """
        Determines whether an operation should be retried based on error count and backoff timing.
        
        Returns:
            True if the operation is eligible for retry; False if the maximum retries have been reached or the backoff period has not elapsed.
        """
        if self.error_count >= 3:  # Max retries
            return False
        
        if self.last_error_time:
            # Implement exponential backoff
            time_since_last = (datetime.now() - self.last_error_time).total_seconds()
            if time_since_last < self.backoff_time:
                return False
            self.backoff_time *= 2  # Double backoff time
            
        return True
        
    def handle_api_error(self, error: Exception) -> None:
        """
        Handles API errors by updating error state and displaying user-friendly messages.
        
        Increments the error count and updates the last error timestamp. Displays
        appropriate Streamlit error messages based on the type of exception and HTTP
        status code, including authentication failures, permission issues, missing
        resources, rate limiting, server errors, timeouts, and WebSocket errors. Applies
        a backoff delay when rate limits are encountered.
        """
        self.error_count += 1
        self.last_error_time = datetime.now()
        
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code == 401:
                st.error("Authentication failed. Please check your credentials.")
            elif status_code == 403:
                st.error("You don't have permission to perform this action.")
            elif status_code == 404:
                st.error("The requested resource was not found.")
            elif status_code == 429:
                st.error("Too many requests. Please wait before trying again.")
                time.sleep(self.backoff_time)  # Respect rate limits
            elif status_code >= 500:
                st.error("Server error. Please try again later.")
            else:
                st.error(f"API error: {str(error)}")
        elif isinstance(error, httpx.TimeoutException):
            st.error("Request timed out. Please try again.")
        elif isinstance(error, WebSocketException):
            st.error("WebSocket connection error. Attempting to reconnect...")
        else:
            st.error(f"Unexpected error: {str(error)}")
            
    def handle_websocket_error(self, error: Exception) -> None:
        """
        Handles errors encountered during WebSocket communication.
        
        Increments the error count and updates the last error timestamp. Displays a Streamlit error message for WebSocket disconnections and applies a backoff delay before attempting to reconnect. For other exceptions, shows a generic WebSocket error message.
        """
        self.error_count += 1
        self.last_error_time = datetime.now()
        
        if isinstance(error, WebSocketException):
            st.error("Lost connection to server. Attempting to reconnect...")
            time.sleep(self.backoff_time)  # Wait before reconnecting
        else:
            st.error(f"WebSocket error: {str(error)}")
            
def with_error_handling(error_handler: ErrorHandler = None):
    """
    Creates a decorator that adds automatic error handling and retry logic to async functions.
    
    The decorated function will be retried on exceptions up to a maximum number of attempts,
    with exponential backoff between retries. If the maximum is reached, a Streamlit error
    message is displayed and the exception is re-raised.
    """
    error_handler = error_handler or ErrorHandler()
    
    def decorator(func: Callable):
        """
        Wraps an asynchronous function with error handling and retry logic.
        
        The decorated function will automatically retry on exceptions, invoking the error handler for each error. Retries continue until the error handler determines no further attempts should be made, after which a user-facing error message is displayed and the exception is re-raised.
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_handler.handle_api_error(e)
                    if not error_handler.should_retry():
                        st.error("Maximum retry attempts reached. Please try again later.")
                        raise
                    continue
        return wrapper
    return decorator

# Example usage:
# @with_error_handling()
# async def api_call():
#     async with httpx.AsyncClient() as client:
#         response = await client.get("http://api.example.com")
#         response.raise_for_status()
#         return response.json() 