"""
Tests for the tool functionality and registry.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from core.tools.web_search import web_search, SearchResult
from wrenchai.core.tool_system import ToolRegistry

class TestWebSearch:
    """Tests for the web search tool."""
    
    @pytest.mark.asyncio
    async def test_web_search_with_duckduckgo(self):
        """Test web search with mocked DuckDuckGo integration."""
        with patch('core.tools.web_search.DUCKDUCKGO_AVAILABLE', True), \
             patch('core.tools.web_search.duckduckgo_search') as mock_search:
            
            # Mock the DuckDuckGo search results
            mock_search.return_value = [
                {"title": "Test Result 1", "href": "https://example.com/1", "body": "This is result 1"},
                {"title": "Test Result 2", "href": "https://example.com/2", "body": "This is result 2"}
            ]
            
            # Call the web search function
            results = await web_search("test query", max_results=2)
            
            # Verify results
            assert len(results) == 2
            assert isinstance(results[0], SearchResult)
            assert results[0].title == "Test Result 1"
            assert results[0].url == "https://example.com/1"
            assert results[0].source == "duckduckgo"
            
    @pytest.mark.asyncio
    async def test_web_search_fallback(self):
        """Test web search fallback when DuckDuckGo is not available."""
        with patch('core.tools.web_search.DUCKDUCKGO_AVAILABLE', False):
            # Call the web search function
            results = await web_search("test query", max_results=3)
            
            # Verify fallback results
            assert len(results) == 3
            assert isinstance(results[0], SearchResult)
            assert "test query" in results[0].title
            assert results[0].source == "placeholder"

class TestToolRegistry:
    """Tests for the tool registry system."""
    
    def test_tool_registry_initialization(self):
        """Test initializing the tool registry."""
        with patch('core.config_loader.load_config') as mock_load:
            # Mock the configuration
            mock_load.return_value = {'tools': []}
            
            # Initialize registry
            registry = ToolRegistry()
            
            # Verify initialization
            assert registry.tools == {}
            mock_load.assert_called_once()
    
    def test_loading_tools(self):
        """Test loading tools from configuration."""
        with patch('core.config_loader.load_config') as mock_load, \
             patch('importlib.import_module') as mock_import:
            
            # Mock implementation
            mock_module = MagicMock()
            mock_module.test_tool = lambda: "test result"
            mock_import.return_value = mock_module
            
            # Mock the configuration
            mock_load.return_value = {
                'tools': [
                    {
                        'name': 'test_tool',
                        'implementation': 'test_module.test_tool',
                        'description': 'A test tool',
                        'parameters': {}
                    }
                ]
            }
            
            # Initialize registry
            registry = ToolRegistry()
            
            # Verify tool was loaded
            assert 'test_tool' in registry.tools
            assert registry.tools['test_tool']['function'] == mock_module.test_tool