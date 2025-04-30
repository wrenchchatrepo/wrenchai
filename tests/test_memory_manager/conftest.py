"""
Pytest configuration for memory manager tests.
"""
import asyncio
import pytest
from typing import Generator

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Creates a dedicated asyncio event loop for the test session.
    
    Yields:
        An asyncio event loop to be used by tests. The loop is closed after the session ends.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 