"""
Puppeteer tool for browser automation.

This module provides a high-level interface for browser automation using Puppeteer.
It supports common operations like navigation, clicking, typing, and taking screenshots.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import asyncio
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class PuppeteerConfig(BaseModel):
    """Configuration for Puppeteer."""
    headless: bool = Field(default=True, description="Whether to run browser in headless mode")
    default_viewport: Dict[str, int] = Field(
        default={"width": 1920, "height": 1080},
        description="Default viewport dimensions"
    )
    timeout: int = Field(default=30000, description="Default timeout in milliseconds")
    screenshot_path: str = Field(
        default="./screenshots",
        description="Path to save screenshots"
    )
    user_data_dir: Optional[str] = Field(
        default=None,
        description="Path to user data directory"
    )

class PuppeteerAction(BaseModel):
    """Represents a Puppeteer action to perform."""
    action_type: str = Field(..., description="Type of action to perform")
    selector: Optional[str] = Field(None, description="CSS selector for element")
    value: Optional[str] = Field(None, description="Value for input actions")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")

class PuppeteerResult(BaseModel):
    """Result of a Puppeteer action."""
    success: bool = Field(..., description="Whether the action was successful")
    data: Optional[Any] = Field(None, description="Result data if any")
    error: Optional[str] = Field(None, description="Error message if action failed")

class PuppeteerTool:
    """Tool for browser automation using Puppeteer."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the PuppeteerTool with optional configuration.
        
        If a configuration dictionary is provided, it is used to set up Puppeteer settings; otherwise, default settings are applied. Ensures the screenshot directory exists.
        """
        self.config = PuppeteerConfig(**(config or {}))
        self._ensure_screenshot_dir()
        
    def _ensure_screenshot_dir(self):
        """
        Creates the screenshot directory if it does not already exist.
        """
        Path(self.config.screenshot_path).mkdir(parents=True, exist_ok=True)
        
    async def _execute_puppeteer_script(self, script: str) -> Dict[str, Any]:
        """
        Asynchronously executes a Puppeteer JavaScript script via MCP and returns the result.
        
        Args:
            script: The JavaScript code to execute in the browser context.
        
        Returns:
            A dictionary containing the execution result or an error message if execution fails.
        """
        try:
            # Use MCP to execute the Puppeteer script
            from mcp.puppeteer import execute_puppeteer
            result = await execute_puppeteer(script)
            return result
        except Exception as e:
            logger.error(f"Error executing Puppeteer script: {e}")
            return {"error": str(e)}
            
    async def navigate(self, url: str, options: Optional[Dict[str, Any]] = None) -> PuppeteerResult:
        """
        Navigates the browser to the specified URL.
        
        Args:
            url: The destination URL.
            options: Optional navigation parameters for Puppeteer.
        
        Returns:
            A PuppeteerResult indicating whether navigation succeeded, with the current URL or an error message.
        """
        script = f"""
        await page.goto('{url}', {json.dumps(options) if options else '{}'});
        return {{ url: page.url() }};
        """
        
        result = await self._execute_puppeteer_script(script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("url"),
            error=result.get("error")
        )
        
    async def click(self, selector: str, options: Optional[Dict[str, Any]] = None) -> PuppeteerResult:
        """
        Clicks the element matching the specified CSS selector.
        
        Args:
            selector: CSS selector identifying the element to click.
            options: Additional options for the click action.
        
        Returns:
            A PuppeteerResult indicating whether the click was successful.
        """
        script = f"""
        await page.click('{selector}', {json.dumps(options) if options else '{}'});
        return {{ clicked: true }};
        """
        
        result = await self._execute_puppeteer_script(script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("clicked"),
            error=result.get("error")
        )
        
    async def type(self, selector: str, text: str, options: Optional[Dict[str, Any]] = None) -> PuppeteerResult:
        """
        Types the specified text into an input element identified by the CSS selector.
        
        Args:
            selector: The CSS selector for the target input element.
            text: The text to type into the element.
            options: Optional dictionary of typing options.
        
        Returns:
            A PuppeteerResult indicating whether the typing action was successful.
        """
        script = f"""
        await page.type('{selector}', '{text}', {json.dumps(options) if options else '{}'});
        return {{ typed: true }};
        """
        
        result = await self._execute_puppeteer_script(script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("typed"),
            error=result.get("error")
        )
        
    async def screenshot(
        self,
        name: str,
        selector: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> PuppeteerResult:
        """
        Captures a screenshot of the page or a specific element and saves it to a file.
        
        If a CSS selector is provided, only the matching element is captured; otherwise, the entire page is saved. The screenshot is stored under the given name in the configured screenshot directory. Additional screenshot options can be supplied.
        
        Args:
            name: The filename (without extension) for the screenshot.
            selector: CSS selector for the element to capture, or None for full-page.
            options: Additional screenshot options for Puppeteer.
        
        Returns:
            A PuppeteerResult indicating success and the path to the saved screenshot, or an error.
        """
        file_path = str(Path(self.config.screenshot_path) / f"{name}.png")
        
        if selector:
            script = f"""
            const element = await page.$('{selector}');
            await element.screenshot({{
                path: '{file_path}',
                ...{json.dumps(options) if options else '{}'}
            }});
            return {{ path: '{file_path}' }};
            """
        else:
            script = f"""
            await page.screenshot({{
                path: '{file_path}',
                ...{json.dumps(options) if options else '{}'}
            }});
            return {{ path: '{file_path}' }};
            """
            
        result = await self._execute_puppeteer_script(script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("path"),
            error=result.get("error")
        )
        
    async def evaluate(self, script: str) -> PuppeteerResult:
        """
        Evaluates JavaScript code in the context of the current page.
        
        Args:
            script: The JavaScript code to execute.
        
        Returns:
            A PuppeteerResult containing the evaluation result or error information.
        """
        wrapped_script = f"""
        const result = await page.evaluate(() => {{
            {script}
        }});
        return {{ result }};
        """
        
        result = await self._execute_puppeteer_script(wrapped_script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("result"),
            error=result.get("error")
        )
        
    async def wait_for_selector(
        self,
        selector: str,
        options: Optional[Dict[str, Any]] = None
    ) -> PuppeteerResult:
        """
        Waits for an element matching the specified CSS selector to appear on the page.
        
        Args:
            selector: The CSS selector of the element to wait for.
            options: Additional options for waiting, such as timeout or visibility.
        
        Returns:
            A PuppeteerResult indicating whether the element appeared.
        """
        script = f"""
        await page.waitForSelector('{selector}', {json.dumps(options) if options else '{}'});
        return {{ waited: true }};
        """
        
        result = await self._execute_puppeteer_script(script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("waited"),
            error=result.get("error")
        )
        
    async def get_text(self, selector: str) -> PuppeteerResult:
        """
        Retrieves the text content of the element matching the given CSS selector.
        
        Args:
            selector: CSS selector identifying the target element.
        
        Returns:
            A PuppeteerResult containing the element's text content if found, or an error message if not.
        """
        script = f"""
        const element = await page.$('{selector}');
        const text = await page.evaluate(el => el.textContent, element);
        return {{ text }};
        """
        
        result = await self._execute_puppeteer_script(script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("text"),
            error=result.get("error")
        )
        
    async def get_attribute(self, selector: str, attribute: str) -> PuppeteerResult:
        """
        Retrieves the value of a specified attribute from the element matching the selector.
        
        Args:
            selector: CSS selector identifying the target element.
            attribute: Name of the attribute to retrieve.
        
        Returns:
            A PuppeteerResult containing the attribute value if found, or an error message.
        """
        script = f"""
        const element = await page.$('{selector}');
        const value = await page.evaluate((el, attr) => el.getAttribute(attr), element, '{attribute}');
        return {{ value }};
        """
        
        result = await self._execute_puppeteer_script(script)
        return PuppeteerResult(
            success="error" not in result,
            data=result.get("value"),
            error=result.get("error")
        )

async def puppeteer_action(action: str, url: str = None, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Dispatches a browser automation action using Puppeteer and returns the result as a dictionary.
    
    Supported actions include navigation, clicking, typing, taking screenshots, evaluating JavaScript, waiting for selectors, and retrieving element text or attributes. Required options depend on the action type.
    
    Args:
        action: The name of the browser automation action to perform.
        url: The target URL for navigation actions.
        options: Additional parameters required for the specified action.
    
    Returns:
        A dictionary containing the result of the action, including success status, data, or error information.
    """
    try:
        tool = PuppeteerTool()
        options = options or {}
        
        if action == "navigate" and url:
            result = await tool.navigate(url, options)
        elif action == "click" and "selector" in options:
            result = await tool.click(options["selector"], options.get("clickOptions"))
        elif action == "type" and "selector" in options and "text" in options:
            result = await tool.type(options["selector"], options["text"], options.get("typeOptions"))
        elif action == "screenshot" and "name" in options:
            result = await tool.screenshot(
                options["name"],
                options.get("selector"),
                options.get("screenshotOptions")
            )
        elif action == "evaluate" and "script" in options:
            result = await tool.evaluate(options["script"])
        elif action == "waitForSelector" and "selector" in options:
            result = await tool.wait_for_selector(options["selector"], options.get("waitOptions"))
        elif action == "getText" and "selector" in options:
            result = await tool.get_text(options["selector"])
        elif action == "getAttribute" and "selector" in options and "attribute" in options:
            result = await tool.get_attribute(options["selector"], options["attribute"])
        else:
            return {
                "error": f"Invalid action '{action}' or missing required options"
            }
            
        return result.dict()
    except Exception as e:
        logger.error(f"Error in puppeteer_action: {e}")
        return {
            "error": str(e)
        } 