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
        """
        Initializes a SearchResult instance with title, URL, snippet, and source.
        
        Args:
            title: The title of the search result.
            url: The URL of the search result.
            snippet: A brief description or snippet from the search result.
            source: The source of the search result (default is "web").
        """
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source

    def to_dict(self) -> Dict[str, str]:
        """
        Returns the search result as a dictionary with title, URL, snippet, and source.
        """
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source
        }

async def search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Performs an asynchronous web search using multiple fallback strategies.
    
    Attempts to retrieve up to `max_results` results for the given query by first searching DuckDuckGo, then Brave Search, and finally a custom placeholder if all else fails. Returns a list of dictionaries containing the title, URL, snippet, and source for each result. Returns an empty list if all search methods fail.
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
    """
    Performs an asynchronous web search using DuckDuckGo and returns search results.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to retrieve.
    
    Returns:
        A list of SearchResult objects containing the search results from DuckDuckGo.
        Returns an empty list if the search fails.
    """
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
    """
    Performs an asynchronous web search using the Brave Search API.
    
    Attempts to retrieve search results for the given query and returns a list of
    SearchResult objects with source set to "brave". Returns an empty list if the
    API key is missing, the API request fails, or an exception occurs.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to retrieve.
    
    Returns:
        A list of SearchResult objects from Brave Search, or an empty list on failure.
    """
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
    """
    Returns placeholder search results as a fallback when other search methods fail.
    
    Args:
        query: The search query string.
        max_results: The number of placeholder results to generate.
    
    Returns:
        A list of SearchResult objects containing generic placeholder content.
    """
    # This is a placeholder implementation
    return [SearchResult(
        title=f"Search result for: {query}",
        url="https://example.com",
        snippet="This is a placeholder result when other search methods fail.",
        source="placeholder"
    ) for _ in range(max_results)]
