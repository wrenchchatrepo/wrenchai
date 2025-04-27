"""
Secrets Audit Tool for WrenchAI.

This module helps audit and validate credentials stored in the keychain.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from .secrets_manager import secrets, SecretNotFoundError

logger = logging.getLogger(__name__)

# Define all expected credentials
REQUIRED_CREDENTIALS = {
    # AI Model APIs (Required)
    'openai_api_key': {
        'description': 'OpenAI API Key',
        'prefix': 'sk-',
        'required': True
    },
    'anthropic_api_key': {
        'description': 'Anthropic API Key (Claude)',
        'prefix': 'sk-ant-',
        'required': True
    },
    'github_token': {
        'description': 'GitHub Personal Access Token',
        'prefix': 'ghp_',
        'required': True
    },
    
    # Google Cloud Platform (Required for core features)
    'gcp_project_id': {
        'description': 'Google Cloud Project ID',
        'prefix': None,
        'required': True
    },
    'gcp_service_account': {
        'description': 'GCP Service Account JSON',
        'prefix': '{',  # JSON always starts with {
        'required': True
    },
    'gemini_api_key': {
        'description': 'Google Gemini API Key',
        'prefix': 'AIza',
        'required': True
    },
    
    # Communication Services (Required)
    'slack_bot_token': {
        'description': 'Slack Bot User OAuth Token',
        'prefix': 'xoxb-',
        'required': True
    },
    'slack_app_token': {
        'description': 'Slack App-Level Token',
        'prefix': 'xapp-',
        'required': True
    },
    
    # Optional AI Model APIs
    'groq_api_key': {
        'description': 'Groq API Key',
        'prefix': 'gsk_',
        'required': False
    },
    'mistral_api_key': {
        'description': 'Mistral API Key',
        'prefix': None,
        'required': False
    },
    'cohere_api_key': {
        'description': 'Cohere API Key',
        'prefix': None,
        'required': False
    },
    'huggingface_token': {
        'description': 'HuggingFace API Token',
        'prefix': 'hf_',
        'required': False
    },
    
    # Cloud Services (Optional)
    'aws_access_key': {
        'description': 'AWS Access Key',
        'prefix': 'AKIA',
        'required': False
    },
    'aws_secret_key': {
        'description': 'AWS Secret Key',
        'prefix': None,
        'required': False
    },
    'azure_api_key': {
        'description': 'Azure API Key',
        'prefix': None,
        'required': False
    },
    
    # Database Credentials (Optional)
    'postgres_password': {
        'description': 'PostgreSQL Database Password',
        'prefix': None,
        'required': False
    },
    'mysql_password': {
        'description': 'MySQL Database Password',
        'prefix': None,
        'required': False
    },
    
    # Monitoring & Analytics (Optional)
    'prometheus_token': {
        'description': 'Prometheus API Token',
        'prefix': None,
        'required': False
    },
    'grafana_api_key': {
        'description': 'Grafana API Key',
        'prefix': None,
        'required': False
    },
    'logfire_api_key': {
        'description': 'Logfire API Key',
        'prefix': None,
        'required': False
    }
}

# Define deprecated credentials that should be removed
DEPRECATED_CREDENTIALS = [
    'old_openai_key',
    'deprecated_github_token',
    'test_api_key',
    'old_slack_token',
    'old_gcp_key',
    'firebase_key',  # If not using Firebase
    'old_azure_key',
    'deprecated_aws_key',
    'old_anthropic_key',
    'test_db_password'
]

async def validate_credential_format(name: str, value: str) -> bool:
    """Validate the format of a credential."""
    if name not in REQUIRED_CREDENTIALS:
        return False
        
    prefix = REQUIRED_CREDENTIALS[name]['prefix']
    if prefix and not value.startswith(prefix):
        logger.warning(f"Credential {name} does not match expected format")
        return False
    return True

async def audit_secrets() -> Dict[str, Dict]:
    """
    Audit all secrets in the keychain.
    
    Returns:
        Dict containing audit results
    """
    audit_results = {
        'timestamp': datetime.now().isoformat(),
        'required_credentials': {},
        'optional_credentials': {},
        'deprecated_credentials': {},
        'unknown_credentials': {},
        'missing_required': []
    }
    
    # Check required and optional credentials
    for cred_name, cred_info in REQUIRED_CREDENTIALS.items():
        try:
            value = await secrets.get_secret(cred_name)
            is_valid = await validate_credential_format(cred_name, value)
            result = {
                'exists': True,
                'valid_format': is_valid,
                'description': cred_info['description']
            }
            
            if cred_info['required']:
                audit_results['required_credentials'][cred_name] = result
            else:
                audit_results['optional_credentials'][cred_name] = result
                
        except SecretNotFoundError:
            if cred_info['required']:
                audit_results['missing_required'].append(cred_name)
    
    # Check for deprecated credentials
    for cred_name in DEPRECATED_CREDENTIALS:
        try:
            await secrets.get_secret(cred_name)
            audit_results['deprecated_credentials'][cred_name] = {
                'exists': True,
                'action': 'Should be removed'
            }
        except SecretNotFoundError:
            pass
    
    return audit_results

async def print_audit_results(results: Dict) -> None:
    """Print formatted audit results."""
    print("\n=== WrenchAI Secrets Audit ===")
    print(f"Timestamp: {results['timestamp']}\n")
    
    print("Required Credentials:")
    for name, info in results['required_credentials'].items():
        status = "✅" if info['valid_format'] else "⚠️"
        print(f"{status} {name}: {info['description']}")
    
    if results['missing_required']:
        print("\nMissing Required Credentials:")
        for name in results['missing_required']:
            print(f"❌ {name}: {REQUIRED_CREDENTIALS[name]['description']}")
    
    print("\nOptional Credentials:")
    for name, info in results['optional_credentials'].items():
        status = "✅" if info['valid_format'] else "⚠️"
        print(f"{status} {name}: {info['description']}")
    
    if results['deprecated_credentials']:
        print("\nDeprecated Credentials (Should be removed):")
        for name in results['deprecated_credentials']:
            print(f"🗑️ {name}")
    
    print("\nRecommended Actions:")
    if results['missing_required']:
        print("1. Add missing required credentials")
    if results['deprecated_credentials']:
        print("2. Remove deprecated credentials")
    if any(not info['valid_format'] for info in results['required_credentials'].values()):
        print("3. Fix invalid credential formats")

async def main():
    """Run the secrets audit."""
    try:
        results = await audit_secrets()
        await print_audit_results(results)
    except Exception as e:
        logger.error(f"Audit failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 