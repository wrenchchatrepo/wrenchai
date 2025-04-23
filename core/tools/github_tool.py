# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import json
import requests
from typing import Dict, Any, Optional

def github_action(action: str, repo: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute GitHub actions using the GitHub API.
    
    Args:
        action: The GitHub action to perform (create_repo, create_issue, create_pr, etc.)
        repo: The target repository (format: owner/repo)
        payload: Action-specific payload data
        
    Returns:
        Dict containing the action result
    """
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")
        
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    base_url = 'https://api.github.com'
    
    try:
        if action == 'create_repo':
            url = f'{base_url}/user/repos'
            response = requests.post(url, headers=headers, json=payload)
            
        elif action == 'create_issue':
            url = f'{base_url}/repos/{repo}/issues'
            response = requests.post(url, headers=headers, json=payload)
            
        elif action == 'create_pr':
            url = f'{base_url}/repos/{repo}/pulls'
            response = requests.post(url, headers=headers, json=payload)
            
        elif action == 'create_file':
            url = f'{base_url}/repos/{repo}/contents/{payload["path"]}'
            response = requests.put(url, headers=headers, json=payload)
            
        elif action == 'update_file':
            url = f'{base_url}/repos/{repo}/contents/{payload["path"]}'
            # Get the current file to obtain its SHA
            current = requests.get(url, headers=headers)
            if current.status_code == 200:
                payload['sha'] = current.json()['sha']
            response = requests.put(url, headers=headers, json=payload)
            
        elif action == 'delete_file':
            url = f'{base_url}/repos/{repo}/contents/{payload["path"]}'
            current = requests.get(url, headers=headers)
            if current.status_code == 200:
                payload['sha'] = current.json()['sha']
            response = requests.delete(url, headers=headers, json=payload)
            
        else:
            return {
                'error': f'Unsupported action: {action}',
                'status': 'error'
            }
            
        response.raise_for_status()
        return {
            'status': 'success',
            'data': response.json(),
            'action': action,
            'repo': repo
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'error': str(e),
            'status': 'error',
            'action': action,
            'repo': repo
        }
