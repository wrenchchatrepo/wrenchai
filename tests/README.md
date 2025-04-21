# Wrenchai Tests

This directory contains tests for the Wrenchai framework, using Pydantic AI's testing capabilities.

## Running Tests

Run all tests with:

```bash
pytest
```

Run specific test files:

```bash
pytest tests/test_agents.py
```

Run with coverage report:

```bash
pytest --cov=wrenchai
```

## Test Structure

- `conftest.py`: Contains shared fixtures and test configuration
- `test_agents.py`: Tests for agent functionality
- `test_tools.py`: Tests for tool functionality and registry

## Testing Philosophy

1. **No Real Model Calls**: Tests use `TestModel` and `FunctionModel` from Pydantic AI to avoid real API calls.
2. **Instrumentation**: Logfire integration provides detailed monitoring during development.
3. **Isolated Tests**: Each test is isolated with its own fixtures and mocks.
4. **Async Support**: Tests support asynchronous execution for API and agent testing.

## Adding New Tests

When adding new tests:

1. Use appropriate fixtures from `conftest.py`
2. Use `@pytest.mark.asyncio` for async tests
3. Use `dirty_equals` for flexible assertions
4. Use `inline_snapshot` for testing complex responses