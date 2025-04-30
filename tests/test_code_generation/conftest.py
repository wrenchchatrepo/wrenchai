"""
Pytest configuration for code generation tests.
"""
import asyncio
import pytest
from typing import Generator

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Creates a dedicated asyncio event loop for the test session.
    
    Yields:
        An asyncio event loop to be used by asynchronous tests. The loop is closed
        after all tests in the session have completed.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 