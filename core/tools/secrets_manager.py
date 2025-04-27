"""
Secrets Manager for WrenchAI.

This module provides secure credential management using macOS Keychain.
It follows the project's security standards and provides a clean API for
managing sensitive information.
"""

import keyring
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, SecretStr
from functools import wraps

logger = logging.getLogger(__name__)

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