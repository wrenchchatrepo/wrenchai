"""
Secrets Manager for WrenchAI.

This module provides secure credential management using macOS Keychain.
It follows the project's security standards and provides a clean API for
managing sensitive information.
"""

import keyring
import logging
import os
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel, SecretStr
from functools import wraps

logger = logging.getLogger(__name__)

# Constants
SERVICE_NAME = "mcp-servers"
DEFAULT_ACCOUNT = "default"

class SecretNotFoundError(Exception):
    """Raised when a secret is not found in the keychain."""
    pass

class SecretStoreError(Exception):
    """Raised when there's an error storing a secret."""
    pass

class Secret(BaseModel):
    """Model for secret data."""
    name: str
    value: SecretStr
    service: str = 'mcp-servers'  # Default service name as per project rules
    
    class Config:
        frozen = True

def handle_keyring_errors(func):
    """Decorator to handle keyring operation errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except keyring.errors.KeyringError as e:
            logger.error(f"Keyring operation failed: {str(e)}")
            raise SecretStoreError(f"Failed to access keychain: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in secrets operation: {str(e)}")
            raise
    return wrapper

class SecretsManager:
    """
    Manages secrets using macOS Keychain.
    
    This class provides a secure interface for storing and retrieving
    sensitive information like API keys and credentials.
    """
    
    def __init__(self, service_name: str = 'mcp-servers'):
        """
        Initialize SecretsManager.
        
        Args:
            service_name: The service name to use in keychain.
                        Defaults to 'mcp-servers' as per project rules.
        """
        self.service_name = service_name
        
    @handle_keyring_errors
    async def store_secret(self, name: str, value: str) -> None:
        """
        Store a secret in the keychain.
        
        Args:
            name: The name/identifier of the secret
            value: The secret value to store
            
        Raises:
            SecretStoreError: If storing the secret fails
        """
        try:
            keyring.set_password(self.service_name, name, value)
            logger.info(f"Successfully stored secret: {name}")
        except Exception as e:
            raise SecretStoreError(f"Failed to store secret {name}: {str(e)}")
    
    @handle_keyring_errors
    async def get_secret(self, name: str) -> str:
        """
        Retrieve a secret from the keychain.
        
        Args:
            name: The name/identifier of the secret
            
        Returns:
            The secret value
            
        Raises:
            SecretNotFoundError: If the secret is not found
            SecretStoreError: If accessing the secret fails
        """
        value = keyring.get_password(self.service_name, name)
        if value is None:
            raise SecretNotFoundError(f"Secret not found: {name}")
        return value
    
    @handle_keyring_errors
    async def delete_secret(self, name: str) -> None:
        """
        Delete a secret from the keychain.
        
        Args:
            name: The name/identifier of the secret to delete
            
        Raises:
            SecretNotFoundError: If the secret is not found
            SecretStoreError: If deleting the secret fails
        """
        try:
            keyring.delete_password(self.service_name, name)
            logger.info(f"Successfully deleted secret: {name}")
        except keyring.errors.PasswordDeleteError:
            raise SecretNotFoundError(f"Secret not found: {name}")
    
    @handle_keyring_errors
    async def update_secret(self, name: str, value: str) -> None:
        """
        Update an existing secret in the keychain.
        
        Args:
            name: The name/identifier of the secret
            value: The new secret value
            
        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretStoreError: If updating the secret fails
        """
        # Check if secret exists first
        if not keyring.get_password(self.service_name, name):
            raise SecretNotFoundError(f"Secret not found: {name}")
        
        await self.store_secret(name, value)
        logger.info(f"Successfully updated secret: {name}")
    
    async def secret_exists(self, name: str) -> bool:
        """
        Check if a secret exists in the keychain.
        
        Args:
            name: The name/identifier of the secret
            
        Returns:
            bool: True if the secret exists, False otherwise
        """
        try:
            return bool(await self.get_secret(name))
        except SecretNotFoundError:
            return False

# Create a global instance for convenience
secrets = SecretsManager()

# Example usage:
"""
# Store an API key
await secrets.store_secret('openai_api_key', 'sk-...')

# Retrieve an API key
api_key = await secrets.get_secret('openai_api_key')

# Update an API key
await secrets.update_secret('openai_api_key', 'new-key-value')

# Delete an API key
await secrets.delete_secret('openai_api_key')

# Check if a secret exists
exists = await secrets.secret_exists('openai_api_key')
"""

async def manage_secrets(action: str, key: str, value: str = None) -> Dict[str, Any]:
    """Manage secure credentials and secrets.
    
    Args:
        action: Action to perform ('get', 'set', 'delete', 'list')
        key: Secret key name
        value: Optional secret value for 'set' action
        
    Returns:
        Dict containing operation result
    """
    try:
        if action == "get":
            return await _get_secret(key)
        elif action == "set":
            return await _set_secret(key, value)
        elif action == "delete":
            return await _delete_secret(key)
        elif action == "list":
            return await _list_secrets()
        else:
            raise ValueError(f"Invalid action: {action}")
            
    except Exception as e:
        logging.error(f"Secrets operation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def _get_secret(key: str) -> Dict[str, Any]:
    """Get a secret value."""
    try:
        value = keyring.get_password(SERVICE_NAME, key)
        if value is None:
            return {
                "success": False,
                "error": f"Secret not found: {key}"
            }
            
        return {
            "success": True,
            "key": key,
            "value": value
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get secret: {str(e)}"
        }

async def _set_secret(key: str, value: str) -> Dict[str, Any]:
    """Set a secret value."""
    try:
        if not value:
            return {
                "success": False,
                "error": "Value cannot be empty"
            }
            
        keyring.set_password(SERVICE_NAME, key, value)
        return {
            "success": True,
            "key": key,
            "message": "Secret stored successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to store secret: {str(e)}"
        }

async def _delete_secret(key: str) -> Dict[str, Any]:
    """Delete a secret."""
    try:
        # Check if secret exists
        if not keyring.get_password(SERVICE_NAME, key):
            return {
                "success": False,
                "error": f"Secret not found: {key}"
            }
            
        keyring.delete_password(SERVICE_NAME, key)
        return {
            "success": True,
            "key": key,
            "message": "Secret deleted successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to delete secret: {str(e)}"
        }

async def _list_secrets() -> Dict[str, Any]:
    """List all secret keys (not values)."""
    try:
        # Note: This is a basic implementation. In production,
        # you would want a more secure way to track secret keys.
        secrets_file = os.path.join(os.path.dirname(__file__), ".secrets_index")
        
        if not os.path.exists(secrets_file):
            return {
                "success": True,
                "keys": []
            }
            
        with open(secrets_file, 'r') as f:
            keys = json.load(f)
            
        return {
            "success": True,
            "keys": keys
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list secrets: {str(e)}"
        }

# Helper functions for external use
async def get_secret(key: str) -> Optional[str]:
    """Helper function to get a secret value directly."""
    result = await _get_secret(key)
    return result.get("value") if result.get("success") else None

async def set_secret(key: str, value: str) -> bool:
    """Helper function to set a secret value directly."""
    result = await _set_secret(key, value)
    return result.get("success", False) 