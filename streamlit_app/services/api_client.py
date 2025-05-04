"""HTTP API Client for the WrenchAI Streamlit application.

This module provides clients for communicating with the WrenchAI backend API,
including the base API client and resource-specific clients.
"""

import time
import json
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, Generic, cast
from datetime import datetime
from urllib.parse import urljoin
import logging

import httpx
import streamlit as st

from streamlit_app.utils.session_state import StateKey, get_state, set_state
from streamlit_app.utils.config_manager import get_config
from streamlit_app.utils.user_preferences import get_api_credentials, get_api_state, update_api_state

logger = logging.getLogger(__name__)

# Type variable for generic resource response
T = TypeVar('T')

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_RETRY_BACKOFF = 2.0


class ApiError(Exception):
    """Exception raised for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        """Initialize the exception.
        
        Args:
            message: Error message
            status_code: HTTP status code that caused the error
            response: Raw response data
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class ApiClient:
    """Base client for communicating with the WrenchAI API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
        verify_ssl: bool = True,
        auth_token: Optional[str] = None,
    ):
        """Initialize the API client.
        
        Args:
            base_url: Base URL for the API (defaults to config value)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Initial delay between retries in seconds
            retry_backoff: Backoff multiplier for subsequent retries
            verify_ssl: Whether to verify SSL certificates
            auth_token: Authentication token (defaults to stored credentials)
        """
        # Get configuration
        config = get_config()
        
        # Set up base URL
        self.base_url = base_url or config.api.base_url
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        # Set up request parameters
        self.timeout = timeout or config.api.timeout
        self.verify_ssl = verify_ssl if verify_ssl is not None else config.api.verify_ssl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        
        # Get credentials if not provided
        if auth_token is None and config.api.auth_enabled:
            credentials = get_api_credentials()
            self.auth_token = credentials.token
        else:
            self.auth_token = auth_token
        
        # Set up HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        
        # Set up additional state
        self.last_request_time = None
        self.last_response_time = None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.close()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers.
        
        Returns:
            Dictionary of auth headers to include in requests
        """
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for an endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full URL for the endpoint
        """
        # Remove leading slash if present to avoid double slashes
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        return urljoin(self.base_url, endpoint)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            json_data: Request body as JSON
            headers: Additional headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response object
            
        Raises:
            ApiError: If the request fails after retries
        """
        url = self._build_url(endpoint)
        auth_headers = self._get_auth_headers()
        combined_headers = {**auth_headers, **(headers or {})}
        request_timeout = timeout or self.timeout
        
        # Start API state tracking
        api_state = get_api_state()
        start_time = time.time()
        self.last_request_time = datetime.now()
        
        # Initialize retry counters
        attempts = 0
        current_delay = self.retry_delay
        last_exception = None
        
        while attempts <= self.max_retries:
            try:
                logger.debug(f"Making request: {method} {url}")
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    headers=combined_headers,
                    timeout=request_timeout,
                )
                
                # Record response time
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                self.last_response_time = datetime.now()
                
                # Update API state with timing information
                api_state.record_request(response_time_ms, is_error=False)
                
                # Check if we need to update rate limit information
                if response.headers.get('X-RateLimit-Remaining'):
                    try:
                        remaining = int(response.headers['X-RateLimit-Remaining'])
                        reset_time = datetime.fromtimestamp(
                            int(response.headers.get('X-RateLimit-Reset', 0))
                        )
                        api_state.update_rate_limits(remaining, reset_time)
                    except (ValueError, TypeError):
                        # Ignore errors parsing rate limit headers
                        pass
                
                # Check for successful response
                if response.status_code < 400:
                    # Update API connection state
                    api_state.update_connection_status(
                        connected=True,
                        status_code=response.status_code
                    )
                    update_api_state(api_state)
                    return response
                
                # Handle rate limiting (status code 429)
                if response.status_code == 429 and attempts < self.max_retries:
                    retry_after = int(response.headers.get('Retry-After', current_delay))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    attempts += 1
                    current_delay *= self.retry_backoff
                    continue
                
                # Handle other error status codes
                error_msg = f"Request failed with status code: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = f"{error_msg} - {error_data['error']}"
                except Exception:
                    # If we can't parse the response as JSON, use the text
                    if response.text:
                        error_msg = f"{error_msg} - {response.text[:100]}"
                
                # Update API state with error
                api_state.update_connection_status(
                    connected=False,
                    status_code=response.status_code,
                    error=error_msg
                )
                api_state.record_request(response_time_ms, is_error=True)
                update_api_state(api_state)
                
                # Raise an exception with the error details
                raise ApiError(
                    message=error_msg,
                    status_code=response.status_code,
                    response=error_data if 'error_data' in locals() else None
                )
                
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                error_msg = f"Request failed: {str(e)}"
                logger.warning(f"{error_msg}. Attempt {attempts + 1}/{self.max_retries + 1}")
                
                if attempts >= self.max_retries:
                    # Update API state with connection error
                    api_state.update_connection_status(
                        connected=False,
                        error=error_msg
                    )
                    api_state.record_request(0, is_error=True)
                    update_api_state(api_state)
                    break
                
                await asyncio.sleep(current_delay)
                attempts += 1
                current_delay *= self.retry_backoff
        
        # If we got here, all retries failed
        error_msg = f"Request failed after {self.max_retries + 1} attempts"
        if last_exception:
            error_msg = f"{error_msg}: {str(last_exception)}"
        
        logger.error(error_msg)
        raise ApiError(message=error_msg)
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """Send a GET request.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response object
        """
        return await self._make_request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """Send a POST request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            json_data: Request body as JSON
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response object
        """
        return await self._make_request(
            method="POST",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """Send a PUT request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            json_data: Request body as JSON
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response object
        """
        return await self._make_request(
            method="PUT",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def patch(
        self,
        endpoint: str,
        data: Optional[Any] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """Send a PATCH request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            json_data: Request body as JSON
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response object
        """
        return await self._make_request(
            method="PATCH",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """Send a DELETE request.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout (overrides default)
            
        Returns:
            Response object
        """
        return await self._make_request(
            method="DELETE",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the API.
        
        Returns:
            Health status information
            
        Raises:
            ApiError: If the health check fails
        """
        try:
            response = await self.get(
                endpoint="health",
                timeout=5.0  # Short timeout for health checks
            )
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise ApiError(f"Health check failed: {str(e)}")
    
    async def get_api_version(self) -> str:
        """Get the API version.
        
        Returns:
            API version string
            
        Raises:
            ApiError: If the version check fails
        """
        try:
            response = await self.get(
                endpoint="version",
                timeout=5.0  # Short timeout for version checks
            )
            data = response.json()
            return data.get("version", "unknown")
        except Exception as e:
            logger.error(f"Version check failed: {str(e)}")
            raise ApiError(f"Version check failed: {str(e)}")
    
    async def get_api_features(self) -> Dict[str, bool]:
        """Get the API features.
        
        Returns:
            Dictionary of API features and their availability
            
        Raises:
            ApiError: If the features check fails
        """
        try:
            response = await self.get(
                endpoint="features",
                timeout=5.0  # Short timeout for features checks
            )
            data = response.json()
            return data.get("features", {})
        except Exception as e:
            logger.error(f"Features check failed: {str(e)}")
            # Return empty features dict instead of raising
            return {}


class ResourceClient(Generic[T]):
    """Base client for a specific API resource."""
    
    def __init__(
        self,
        api_client: ApiClient,
        resource_path: str,
        response_model: Callable[[Dict[str, Any]], T],
    ):
        """Initialize the resource client.
        
        Args:
            api_client: Base API client
            resource_path: Path to the resource (e.g., "playbooks")
            response_model: Function to convert API response to model
        """
        self.api_client = api_client
        self.resource_path = resource_path
        self.response_model = response_model
    
    def _get_resource_url(self, resource_id: Optional[str] = None) -> str:
        """Build the URL for a resource.
        
        Args:
            resource_id: Optional resource ID
            
        Returns:
            Resource URL
        """
        url = self.resource_path
        if resource_id:
            url = f"{url}/{resource_id}"
        return url
    
    async def list(
        self,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[T]:
        """List resources.
        
        Args:
            params: Query parameters
            **kwargs: Additional parameters to pass to the API client
            
        Returns:
            List of resource models
            
        Raises:
            ApiError: If the request fails
        """
        response = await self.api_client.get(
            endpoint=self._get_resource_url(),
            params=params,
            **kwargs
        )
        data = response.json()
        items = data.get("items", [])
        return [self.response_model(item) for item in items]
    
    async def get(
        self,
        resource_id: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> T:
        """Get a specific resource.
        
        Args:
            resource_id: Resource ID
            params: Query parameters
            **kwargs: Additional parameters to pass to the API client
            
        Returns:
            Resource model
            
        Raises:
            ApiError: If the request fails
        """
        response = await self.api_client.get(
            endpoint=self._get_resource_url(resource_id),
            params=params,
            **kwargs
        )
        data = response.json()
        return self.response_model(data)
    
    async def create(
        self,
        data: Dict[str, Any],
        **kwargs
    ) -> T:
        """Create a resource.
        
        Args:
            data: Resource data
            **kwargs: Additional parameters to pass to the API client
            
        Returns:
            Created resource model
            
        Raises:
            ApiError: If the request fails
        """
        response = await self.api_client.post(
            endpoint=self._get_resource_url(),
            json_data=data,
            **kwargs
        )
        data = response.json()
        return self.response_model(data)
    
    async def update(
        self,
        resource_id: str,
        data: Dict[str, Any],
        **kwargs
    ) -> T:
        """Update a resource.
        
        Args:
            resource_id: Resource ID
            data: Resource data
            **kwargs: Additional parameters to pass to the API client
            
        Returns:
            Updated resource model
            
        Raises:
            ApiError: If the request fails
        """
        response = await self.api_client.put(
            endpoint=self._get_resource_url(resource_id),
            json_data=data,
            **kwargs
        )
        data = response.json()
        return self.response_model(data)
    
    async def patch(
        self,
        resource_id: str,
        data: Dict[str, Any],
        **kwargs
    ) -> T:
        """Partially update a resource.
        
        Args:
            resource_id: Resource ID
            data: Resource data
            **kwargs: Additional parameters to pass to the API client
            
        Returns:
            Updated resource model
            
        Raises:
            ApiError: If the request fails
        """
        response = await self.api_client.patch(
            endpoint=self._get_resource_url(resource_id),
            json_data=data,
            **kwargs
        )
        data = response.json()
        return self.response_model(data)
    
    async def delete(
        self,
        resource_id: str,
        **kwargs
    ) -> bool:
        """Delete a resource.
        
        Args:
            resource_id: Resource ID
            **kwargs: Additional parameters to pass to the API client
            
        Returns:
            True if successful
            
        Raises:
            ApiError: If the request fails
        """
        await self.api_client.delete(
            endpoint=self._get_resource_url(resource_id),
            **kwargs
        )
        return True