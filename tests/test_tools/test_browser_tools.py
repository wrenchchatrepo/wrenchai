"""Tests for the Browser Tools."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from core.tools.browser_tools import (
    BrowserTools,
    ConsoleLog,
    NetworkLog,
    ElementInfo,
    browser_action,
    BrowserState,
    browser_state,
    get_console_logs,
    get_console_errors,
    get_network_error_logs,
    get_network_success_logs,
    take_screenshot,
    get_selected_element,
    wipe_logs,
    handle_console_log,
    handle_network_request,
    handle_network_response,
    handle_network_error,
    handle_element_selected,
    LogLevel,
    NetworkRequestType,
    NetworkRequest
)
from core.tools.puppeteer import PuppeteerResult

@pytest.fixture
def mock_puppeteer():
    """Mock PuppeteerTool."""
    with patch('core.tools.browser_tools.PuppeteerTool') as mock:
        mock_tool = MagicMock()
        mock.return_value = mock_tool
        yield mock_tool

@pytest.fixture
async def browser_tools(mock_puppeteer):
    """Create a BrowserTools instance with mocked Puppeteer."""
    tools = BrowserTools()
    await tools.setup()
    return tools

@pytest.fixture
def clean_browser_state():
    """Provide a clean browser state for each test."""
    browser_state.clear_logs()
    yield browser_state
    browser_state.clear_logs()

@pytest.fixture
def sample_console_log():
    """Create a sample console log."""
    return ConsoleLog(
        level=LogLevel.INFO,
        message="Test message",
        source="test.js",
        line_number=42
    )

@pytest.fixture
def sample_error_log():
    """Create a sample error log."""
    return ConsoleLog(
        level=LogLevel.ERROR,
        message="Test error",
        source="test.js",
        line_number=42,
        stack_trace="Error stack trace"
    )

@pytest.fixture
def sample_network_request():
    """Create a sample network request."""
    return NetworkRequest(
        request_id="test_request",
        type=NetworkRequestType.XHR,
        method="GET",
        url="https://api.test.com/data",
        status=200,
        status_text="OK",
        request_headers={"Accept": "application/json"},
        response_headers={"Content-Type": "application/json"},
        duration=100.0
    )

@pytest.fixture
def sample_failed_request():
    """Create a sample failed network request."""
    return NetworkRequest(
        request_id="failed_request",
        type=NetworkRequestType.XHR,
        method="GET",
        url="https://api.test.com/error",
        status=500,
        status_text="Internal Server Error",
        success=False,
        error="Server error"
    )

@pytest.fixture
def sample_network_log():
    """Create a sample network log."""
    return NetworkLog(
        timestamp=datetime.utcnow(),
        method="GET",
        url="https://api.test.com/data",
        status=200,
        duration=150.5,
        request_headers={"Accept": "application/json"},
        response_headers={"Content-Type": "application/json"}
    )

@pytest.mark.asyncio
async def test_setup(mock_puppeteer):
    """Test browser tools setup."""
    tools = BrowserTools()
    await tools.setup()
    
    mock_puppeteer.evaluate.assert_called_once()
    script = mock_puppeteer.evaluate.call_args[0][0]
    assert "page.on('console'" in script
    assert "page.on('request'" in script
    assert "page.on('response'" in script

@pytest.mark.asyncio
async def test_get_console_logs(clean_browser_state, sample_console_log):
    """Test getting console logs."""
    # Add some logs
    clean_browser_state.add_console_log(sample_console_log)
    
    # Get logs
    result = await get_console_logs()
    
    assert result["success"]
    assert len(result["logs"]) == 1
    assert result["logs"][0]["message"] == "Test message"
    assert result["logs"][0]["level"] == LogLevel.INFO

@pytest.mark.asyncio
async def test_get_console_errors(clean_browser_state, sample_error_log):
    """Test getting console errors."""
    # Add some errors
    clean_browser_state.add_console_log(sample_error_log)
    
    # Get errors
    result = await get_console_errors()
    
    assert result["success"]
    assert len(result["errors"]) == 1
    assert result["errors"][0]["message"] == "Test error"
    assert result["errors"][0]["level"] == LogLevel.ERROR

@pytest.mark.asyncio
async def test_get_network_logs(mock_puppeteer, browser_tools):
    """Test getting network logs."""
    mock_logs = [
        {
            "method": "GET",
            "url": "https://example.com",
            "status": 200,
            "timestamp": datetime.now().isoformat(),
            "request_headers": {"Accept": "*/*"},
            "response_headers": {"Content-Type": "text/html"}
        }
    ]
    
    mock_puppeteer.evaluate.return_value = PuppeteerResult(
        success=True,
        data=mock_logs
    )
    
    logs = await browser_tools.get_network_logs()
    
    assert len(logs) == 1
    assert isinstance(logs[0], NetworkLog)
    assert logs[0].method == "GET"
    assert logs[0].status == 200
    
    assert mock_puppeteer.evaluate.call_args[0][0] == "window._networkLogs || []"

@pytest.mark.asyncio
async def test_get_network_errors(mock_puppeteer, browser_tools):
    """Test getting network errors."""
    mock_logs = [
        {
            "method": "GET",
            "url": "https://example.com",
            "status": 404,
            "timestamp": datetime.now().isoformat(),
            "request_headers": {},
            "response_headers": {}
        },
        {
            "method": "GET",
            "url": "https://example.com/error",
            "error": "Failed to fetch",
            "timestamp": datetime.now().isoformat(),
            "request_headers": {},
            "response_headers": {}
        },
        {
            "method": "GET",
            "url": "https://example.com/success",
            "status": 200,
            "timestamp": datetime.now().isoformat(),
            "request_headers": {},
            "response_headers": {}
        }
    ]
    
    mock_puppeteer.evaluate.return_value = PuppeteerResult(
        success=True,
        data=mock_logs
    )
    
    errors = await browser_tools.get_network_errors()
    
    assert len(errors) == 2
    assert all(isinstance(error, NetworkLog) for error in errors)
    assert any(error.status == 404 for error in errors)
    assert any(error.error == "Failed to fetch" for error in errors)

@pytest.mark.asyncio
async def test_get_element_info(mock_puppeteer, browser_tools):
    """Test getting element information."""
    mock_info = {
        "tag_name": "div",
        "attributes": {"class": "test-class", "id": "test-id"},
        "text_content": "Test content",
        "inner_html": "<span>Test</span>",
        "outer_html": "<div class='test-class' id='test-id'><span>Test</span></div>",
        "bounding_box": {"x": 0, "y": 0, "width": 100, "height": 50}
    }
    
    mock_puppeteer.evaluate.return_value = PuppeteerResult(
        success=True,
        data=mock_info
    )
    
    info = await browser_tools.get_element_info("#test-id")
    
    assert isinstance(info, ElementInfo)
    assert info.tag_name == "div"
    assert info.attributes["id"] == "test-id"
    assert info.text_content == "Test content"
    assert info.bounding_box["width"] == 100

@pytest.mark.asyncio
async def test_take_screenshot(mock_puppeteer, browser_tools):
    """Test taking a screenshot."""
    mock_result = PuppeteerResult(
        success=True,
        data="/path/to/screenshot.png"
    )
    
    mock_puppeteer.screenshot.return_value = mock_result
    
    result = await browser_tools.take_screenshot(
        "test",
        selector="#test-id",
        full_page=True
    )
    
    assert result.success
    assert result.data == "/path/to/screenshot.png"
    
    mock_puppeteer.screenshot.assert_called_once_with(
        "test",
        "#test-id",
        {"fullPage": True}
    )

@pytest.mark.asyncio
async def test_clear_logs(mock_puppeteer, browser_tools):
    """Test clearing logs."""
    await browser_tools.clear_logs()
    
    mock_puppeteer.evaluate.assert_called_with("""
        window._consoleLogs = [];
        window._networkLogs = [];
        """)

@pytest.mark.asyncio
async def test_browser_action_get_console_logs():
    """Test browser_action with getConsoleLogs."""
    with patch('core.tools.browser_tools.BrowserTools') as MockTools:
        mock_tools = MagicMock()
        mock_tools.get_console_logs.return_value = [
            ConsoleLog(
                level="info",
                message="Test",
                source="test",
                timestamp=datetime.now()
            )
        ]
        MockTools.return_value = mock_tools
        
        result = await browser_action("getConsoleLogs")
        
        assert "logs" in result
        assert len(result["logs"]) == 1
        assert result["logs"][0]["level"] == "info"
        
        mock_tools.setup.assert_called_once()

@pytest.mark.asyncio
async def test_browser_action_get_element_info():
    """Test browser_action with getElementInfo."""
    with patch('core.tools.browser_tools.BrowserTools') as MockTools:
        mock_tools = MagicMock()
        mock_tools.get_element_info.return_value = ElementInfo(
            tag_name="div",
            attributes={"id": "test"},
            text_content="Test"
        )
        MockTools.return_value = mock_tools
        
        result = await browser_action(
            "getElementInfo",
            selector="#test"
        )
        
        assert "element" in result
        assert result["element"]["tag_name"] == "div"
        assert result["element"]["attributes"]["id"] == "test"
        
        mock_tools.setup.assert_called_once()

@pytest.mark.asyncio
async def test_browser_action_invalid():
    """Test browser_action with invalid action."""
    result = await browser_action("invalidAction")
    
    assert "error" in result
    assert "Invalid action" in result["error"]

@pytest.mark.asyncio
async def test_browser_action_error():
    """Test browser_action error handling."""
    with patch('core.tools.browser_tools.BrowserTools') as MockTools:
        mock_tools = MagicMock()
        mock_tools.get_console_logs.side_effect = Exception("Test error")
        MockTools.return_value = mock_tools
        
        result = await browser_action("getConsoleLogs")
        
        assert "error" in result
        assert "Test error" in result["error"]
        
        mock_tools.setup.assert_called_once()

@pytest.mark.asyncio
async def test_get_network_success_logs(clean_browser_state, sample_network_request):
    """Test getting successful network requests."""
    # Add some requests
    clean_browser_state.add_network_request(sample_network_request)
    
    # Get requests
    result = await get_network_success_logs()
    
    assert result["success"]
    assert len(result["requests"]) == 1
    assert result["requests"][0]["status"] == 200
    assert result["requests"][0]["url"] == "https://api.test.com/data"

@pytest.mark.asyncio
async def test_get_network_error_logs(clean_browser_state, sample_failed_request):
    """Test getting failed network requests."""
    # Add some failed requests
    clean_browser_state.add_network_request(sample_failed_request)
    
    # Get errors
    result = await get_network_error_logs()
    
    assert result["success"]
    assert len(result["errors"]) == 1
    assert result["errors"][0]["status"] == 500
    assert result["errors"][0]["error"] == "Server error"

@pytest.mark.asyncio
async def test_take_screenshot_success():
    """Test successful screenshot capture."""
    result = await take_screenshot()
    
    assert result["success"]
    assert "screenshot" in result
    assert "timestamp" in result["screenshot"]
    assert "metadata" in result["screenshot"]

@pytest.mark.asyncio
async def test_get_selected_element_none(clean_browser_state):
    """Test getting selected element when none is selected."""
    result = await get_selected_element()
    
    assert not result["success"]
    assert "No element selected" in result["error"]

@pytest.mark.asyncio
async def test_get_selected_element(clean_browser_state):
    """Test getting selected element."""
    # Set selected element
    element = {
        "tag": "button",
        "id": "test-button",
        "text": "Click me"
    }
    clean_browser_state.set_selected_element(element)
    
    # Get element
    result = await get_selected_element()
    
    assert result["success"]
    assert result["element"]["tag"] == "button"
    assert result["element"]["id"] == "test-button"

@pytest.mark.asyncio
async def test_wipe_logs(
    clean_browser_state,
    sample_console_log,
    sample_error_log,
    sample_network_request,
    sample_failed_request
):
    """Test wiping all logs."""
    # Add various logs
    clean_browser_state.add_console_log(sample_console_log)
    clean_browser_state.add_console_log(sample_error_log)
    clean_browser_state.add_network_request(sample_network_request)
    clean_browser_state.add_network_request(sample_failed_request)
    
    # Verify logs were added
    assert len(clean_browser_state.console_logs) > 0
    assert len(clean_browser_state.console_errors) > 0
    assert len(clean_browser_state.network_success_logs) > 0
    assert len(clean_browser_state.network_error_logs) > 0
    
    # Wipe logs
    result = await wipe_logs()
    
    assert result["success"]
    assert len(clean_browser_state.console_logs) == 0
    assert len(clean_browser_state.console_errors) == 0
    assert len(clean_browser_state.network_success_logs) == 0
    assert len(clean_browser_state.network_error_logs) == 0

def test_browser_state_log_limits():
    """Test that browser state enforces log limits."""
    state = BrowserState()
    
    # Add more logs than the limit
    for i in range(2000):
        log = ConsoleLog(
            level=LogLevel.INFO,
            message=f"Log {i}",
            source="test.js"
        )
        state.add_console_log(log)
    
    # Verify logs were trimmed
    assert len(state.console_logs) == state._max_logs

def test_network_request_type_validation():
    """Test network request type validation."""
    # Valid request type
    request = NetworkRequest(
        request_id="test",
        type=NetworkRequestType.XHR,
        method="GET",
        url="https://test.com"
    )
    assert request.type == NetworkRequestType.XHR
    
    # Invalid request type
    with pytest.raises(ValueError):
        NetworkRequest(
            request_id="test",
            type="invalid_type",
            method="GET",
            url="https://test.com"
        )

def test_log_level_validation():
    """Test log level validation."""
    # Valid log level
    log = ConsoleLog(
        level=LogLevel.INFO,
        message="Test",
        source="test.js"
    )
    assert log.level == LogLevel.INFO
    
    # Invalid log level
    with pytest.raises(ValueError):
        ConsoleLog(
            level="invalid_level",
            message="Test",
            source="test.js"
        )

def test_handle_console_log():
    """Test console log handling."""
    browser_state.clear()
    
    handle_console_log("info", "Test message", "test.js", 42)
    assert len(browser_state.console_logs) == 1
    assert browser_state.console_logs[0].message == "Test message"
    
    handle_console_log("error", "Error message", "test.js", 43)
    assert len(browser_state.error_logs) == 1
    assert browser_state.error_logs[0].message == "Error message"

def test_handle_network_request():
    """Test network request handling."""
    browser_state.clear()
    
    handle_network_request(
        "GET",
        "https://api.test.com/data",
        {"Accept": "application/json"}
    )
    
    assert len(browser_state.network_logs) == 1
    assert browser_state.network_logs[0].method == "GET"
    assert browser_state.network_logs[0].url == "https://api.test.com/data"

def test_handle_network_response():
    """Test network response handling."""
    browser_state.clear()
    
    handle_network_request("GET", "https://api.test.com/data")
    handle_network_response(
        "https://api.test.com/data",
        200,
        150.5,
        {"Content-Type": "application/json"}
    )
    
    assert len(browser_state.network_logs) == 1
    assert browser_state.network_logs[0].status == 200
    assert browser_state.network_logs[0].duration == 150.5

def test_handle_network_error():
    """Test network error handling."""
    browser_state.clear()
    
    handle_network_request("GET", "https://api.test.com/error")
    handle_network_error("https://api.test.com/error", "Connection failed")
    
    assert len(browser_state.network_logs) == 1
    assert browser_state.network_logs[0].error == "Connection failed"

def test_handle_element_selected():
    """Test element selection handling."""
    browser_state.clear()
    
    element_info = {
        "tagName": "div",
        "id": "test-element",
        "className": "test-class"
    }
    handle_element_selected(element_info)
    
    assert browser_state.selected_element == element_info 