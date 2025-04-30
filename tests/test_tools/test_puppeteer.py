"""Tests for the Puppeteer tool."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.tools.puppeteer import (
    PuppeteerTool,
    PuppeteerConfig,
    PuppeteerAction,
    PuppeteerResult,
    puppeteer_action
)

@pytest.fixture
def mock_execute_puppeteer():
    """Mock the execute_puppeteer function."""
    with patch('mcp.puppeteer.execute_puppeteer') as mock:
        yield mock

@pytest.fixture
def puppeteer_tool():
    """Create a PuppeteerTool instance."""
    return PuppeteerTool()

@pytest.mark.asyncio
async def test_navigate(mock_execute_puppeteer, puppeteer_tool):
    """Test navigation to a URL."""
    url = "https://example.com"
    mock_execute_puppeteer.return_value = {"url": url}
    
    result = await puppeteer_tool.navigate(url)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data == url
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    script = mock_execute_puppeteer.call_args[0][0]
    assert url in script
    assert "page.goto" in script

@pytest.mark.asyncio
async def test_click(mock_execute_puppeteer, puppeteer_tool):
    """Test clicking an element."""
    selector = "#button"
    mock_execute_puppeteer.return_value = {"clicked": True}
    
    result = await puppeteer_tool.click(selector)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data is True
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    script = mock_execute_puppeteer.call_args[0][0]
    assert selector in script
    assert "page.click" in script

@pytest.mark.asyncio
async def test_type(mock_execute_puppeteer, puppeteer_tool):
    """Test typing text into an element."""
    selector = "#input"
    text = "Hello, World!"
    mock_execute_puppeteer.return_value = {"typed": True}
    
    result = await puppeteer_tool.type(selector, text)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data is True
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    script = mock_execute_puppeteer.call_args[0][0]
    assert selector in script
    assert text in script
    assert "page.type" in script

@pytest.mark.asyncio
async def test_screenshot(mock_execute_puppeteer, puppeteer_tool, tmp_path):
    """Test taking a screenshot."""
    name = "test_screenshot"
    mock_execute_puppeteer.return_value = {"path": str(tmp_path / f"{name}.png")}
    
    # Set screenshot path to temp directory
    puppeteer_tool.config.screenshot_path = str(tmp_path)
    
    result = await puppeteer_tool.screenshot(name)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data == str(tmp_path / f"{name}.png")
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    script = mock_execute_puppeteer.call_args[0][0]
    assert "screenshot" in script
    assert str(tmp_path) in script

@pytest.mark.asyncio
async def test_evaluate(mock_execute_puppeteer, puppeteer_tool):
    """Test evaluating JavaScript."""
    script = "document.title"
    expected_result = "Page Title"
    mock_execute_puppeteer.return_value = {"result": expected_result}
    
    result = await puppeteer_tool.evaluate(script)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data == expected_result
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    executed_script = mock_execute_puppeteer.call_args[0][0]
    assert script in executed_script
    assert "page.evaluate" in executed_script

@pytest.mark.asyncio
async def test_wait_for_selector(mock_execute_puppeteer, puppeteer_tool):
    """Test waiting for a selector."""
    selector = "#element"
    mock_execute_puppeteer.return_value = {"waited": True}
    
    result = await puppeteer_tool.wait_for_selector(selector)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data is True
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    script = mock_execute_puppeteer.call_args[0][0]
    assert selector in script
    assert "waitForSelector" in script

@pytest.mark.asyncio
async def test_get_text(mock_execute_puppeteer, puppeteer_tool):
    """Test getting element text."""
    selector = "#text"
    expected_text = "Hello, World!"
    mock_execute_puppeteer.return_value = {"text": expected_text}
    
    result = await puppeteer_tool.get_text(selector)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data == expected_text
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    script = mock_execute_puppeteer.call_args[0][0]
    assert selector in script
    assert "textContent" in script

@pytest.mark.asyncio
async def test_get_attribute(mock_execute_puppeteer, puppeteer_tool):
    """Test getting element attribute."""
    selector = "#link"
    attribute = "href"
    expected_value = "https://example.com"
    mock_execute_puppeteer.return_value = {"value": expected_value}
    
    result = await puppeteer_tool.get_attribute(selector, attribute)
    
    assert isinstance(result, PuppeteerResult)
    assert result.success
    assert result.data == expected_value
    assert result.error is None
    
    mock_execute_puppeteer.assert_called_once()
    script = mock_execute_puppeteer.call_args[0][0]
    assert selector in script
    assert attribute in script
    assert "getAttribute" in script

@pytest.mark.asyncio
async def test_puppeteer_action_navigate():
    """Test puppeteer_action with navigate action."""
    with patch('core.tools.puppeteer.PuppeteerTool') as MockTool:
        mock_tool = MagicMock()
        mock_tool.navigate.return_value = PuppeteerResult(
            success=True,
            data="https://example.com"
        )
        MockTool.return_value = mock_tool
        
        result = await puppeteer_action(
            action="navigate",
            url="https://example.com"
        )
        
        assert result["success"]
        assert result["data"] == "https://example.com"
        mock_tool.navigate.assert_called_once_with(
            "https://example.com",
            {}
        )

@pytest.mark.asyncio
async def test_puppeteer_action_click():
    """Test puppeteer_action with click action."""
    with patch('core.tools.puppeteer.PuppeteerTool') as MockTool:
        mock_tool = MagicMock()
        mock_tool.click.return_value = PuppeteerResult(
            success=True,
            data=True
        )
        MockTool.return_value = mock_tool
        
        result = await puppeteer_action(
            action="click",
            options={"selector": "#button"}
        )
        
        assert result["success"]
        assert result["data"] is True
        mock_tool.click.assert_called_once_with(
            "#button",
            None
        )

@pytest.mark.asyncio
async def test_puppeteer_action_invalid():
    """Test puppeteer_action with invalid action."""
    result = await puppeteer_action(
        action="invalid_action"
    )
    
    assert "error" in result
    assert "Invalid action" in result["error"]

@pytest.mark.asyncio
async def test_puppeteer_action_error():
    """Test puppeteer_action error handling."""
    with patch('core.tools.puppeteer.PuppeteerTool') as MockTool:
        mock_tool = MagicMock()
        mock_tool.navigate.side_effect = Exception("Test error")
        MockTool.return_value = mock_tool
        
        result = await puppeteer_action(
            action="navigate",
            url="https://example.com"
        )
        
        assert "error" in result
        assert "Test error" in result["error"] 