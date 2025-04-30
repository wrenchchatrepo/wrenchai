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
        """Initialize Puppeteer tool.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = PuppeteerConfig(**(config or {}))
        self._ensure_screenshot_dir()
        
    def _ensure_screenshot_dir(self):
        """Ensure screenshot directory exists."""
        Path(self.config.screenshot_path).mkdir(parents=True, exist_ok=True)
        
    async def _execute_puppeteer_script(self, script: str) -> Dict[str, Any]:
        """Execute a Puppeteer script using MCP.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Dictionary containing the result
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
        """Navigate to a URL.
        
        Args:
            url: URL to navigate to
            options: Optional navigation options
            
        Returns:
            PuppeteerResult with navigation status
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
        """Click an element.
        
        Args:
            selector: CSS selector for element
            options: Optional click options
            
        Returns:
            PuppeteerResult indicating click success
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
        """Type text into an element.
        
        Args:
            selector: CSS selector for input element
            text: Text to type
            options: Optional typing options
            
        Returns:
            PuppeteerResult indicating typing success
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
        """Take a screenshot.
        
        Args:
            name: Name for the screenshot file
            selector: Optional CSS selector to screenshot specific element
            options: Optional screenshot options
            
        Returns:
            PuppeteerResult with screenshot path
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
        """Evaluate JavaScript in the page context.
        
        Args:
            script: JavaScript code to evaluate
            
        Returns:
            PuppeteerResult with evaluation result
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
        """Wait for an element matching selector.
        
        Args:
            selector: CSS selector to wait for
            options: Optional waiting options
            
        Returns:
            PuppeteerResult indicating wait success
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
        """Get text content of an element.
        
        Args:
            selector: CSS selector for element
            
        Returns:
            PuppeteerResult with element text
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
        """Get attribute value of an element.
        
        Args:
            selector: CSS selector for element
            attribute: Attribute name to get
            
        Returns:
            PuppeteerResult with attribute value
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
    """Main entry point for Puppeteer tool.
    
    Args:
        action: Action to perform
        url: URL for navigation actions
        options: Additional options for the action
        
    Returns:
        Dictionary containing the action result
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