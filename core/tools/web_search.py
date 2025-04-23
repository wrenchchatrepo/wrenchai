# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import json
import requests
from typing import List, Dict, Any, Optional

def search(query: str, max_results: Optional[int] = 5) -> Dict[str, Any]:
    """Search the web using Brave Search API.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        Dict containing search results and metadata
    """
    api_key = os.getenv('BRAVE_SEARCH_API_KEY')
    if not api_key:
        raise ValueError("BRAVE_SEARCH_API_KEY environment variable not set")
        
    headers = {
        'X-Subscription-Token': api_key,
        'Accept': 'application/json'
    }
    
    params = {
        'q': query,
        'count': max_results
    }
    
    try:
        response = requests.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers=headers,
            params=params
        )
        response.raise_for_status()
        
        results = response.json()
        
        # Format the results
        formatted_results = {
            'query': query,
            'total_results': len(results.get('web', {}).get('results', [])),
            'results': []
        }
        
        for result in results.get('web', {}).get('results', [])[:max_results]:
            formatted_results['results'].append({
                'title': result.get('title'),
                'url': result.get('url'),
                'description': result.get('description'),
                'published_date': result.get('published_date')
            })
            
        return formatted_results
        
    except requests.exceptions.RequestException as e:
        return {
            'error': str(e),
            'query': query,
            'total_results': 0,
            'results': []
        }
