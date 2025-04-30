# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import json
import requests
from typing import List, Dict, Any, Optional
import aiohttp
import logging
from bs4 import BeautifulSoup

class SearchResult:
    """Container for search results."""
    def __init__(self, title: str, url: str, snippet: str, source: str = "web"):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source
        }

async def search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search the web for information.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of search results with title, URL, and snippet
    """
    try:
        # First try DuckDuckGo
        results = await _search_duckduckgo(query, max_results)
        if results:
            return [r.to_dict() for r in results]
            
        # Fallback to Brave Search
        results = await _search_brave(query, max_results)
        if results:
            return [r.to_dict() for r in results]
            
        # Final fallback to custom implementation
        results = await _search_custom(query, max_results)
        return [r.to_dict() for r in results]
        
    except Exception as e:
        logging.error(f"Search failed: {str(e)}")
        return []

async def _search_duckduckgo(query: str, max_results: int) -> List[SearchResult]:
    """Search using DuckDuckGo."""
    try:
        from duckduckgo_search import ddg
        
        results = []
        for r in ddg(query, max_results=max_results):
            results.append(SearchResult(
                title=r['title'],
                url=r['link'],
                snippet=r['snippet'],
                source="duckduckgo"
            ))
        return results
    except Exception as e:
        logging.warning(f"DuckDuckGo search failed: {str(e)}")
        return []

async def _search_brave(query: str, max_results: int) -> List[SearchResult]:
    """Search using Brave Search API."""
    try:
        # Get API key from secrets manager
        from core.tools.secrets_manager import get_secret
        api_key = await get_secret("brave_search_api_key")
        
        if not api_key:
            return []
            
        async with aiohttp.ClientSession() as session:
            headers = {
                "X-Subscription-Token": api_key,
                "Accept": "application/json"
            }
            
            async with session.get(
                f"https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params={"q": query, "count": max_results}
            ) as response:
                
                if response.status != 200:
                    return []
                    
                data = await response.json()
                results = []
                
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item["title"],
                        url=item["url"],
                        snippet=item["description"],
                        source="brave"
                    ))
                return results
                
    except Exception as e:
        logging.warning(f"Brave search failed: {str(e)}")
        return []

async def _search_custom(query: str, max_results: int) -> List[SearchResult]:
    """Custom search implementation as final fallback."""
    # This is a placeholder implementation
    return [SearchResult(
        title=f"Search result for: {query}",
        url="https://example.com",
        snippet="This is a placeholder result when other search methods fail.",
        source="placeholder"
    ) for _ in range(max_results)]
