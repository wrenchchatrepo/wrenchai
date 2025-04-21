# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Try to import the DuckDuckGo search tool from Pydantic AI
try:
    from pydantic_ai.common.tools.duckduckgo import duckduckgo_search
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False
    
class SearchResult(BaseModel):
    """Model for search results"""
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = None
    source: str = "custom"

async def web_search(query: str, max_results: int = 5) -> List[SearchResult]:
    """
    Perform a web search using available search providers
    
    Args:
        query: The search query
        max_results: Maximum number of results to return
        
    Returns:
        List of search results with title, URL and snippet
    """
    if DUCKDUCKGO_AVAILABLE:
        # Use the Pydantic AI DuckDuckGo search
        raw_results = await duckduckgo_search(query, max_results=max_results)
        
        # Convert to our standard format
        results = [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("href", ""),
                snippet=item.get("body", ""),
                source="duckduckgo"
            )
            for item in raw_results
        ]
        return results
    else:
        # Fallback to placeholder implementation
        print(f"Performing web search for: {query}")
        return [
            SearchResult(
                title=f"Result {i} for {query}",
                url=f"https://example.com/result{i}",
                snippet=f"This is a placeholder result {i} for the query: {query}",
                source="placeholder"
            )
            for i in range(1, max_results + 1)
        ]

# For backward compatibility
def sync_web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Synchronous version of web_search for compatibility"""
    results = asyncio.run(web_search(query, max_results))
    return [result.model_dump() for result in results]
