# Testing Guide for Nexus

Complete guide for running, writing, and understanding Nexus tests.

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Options

```bash
pytest -v                          # Verbose output
pytest --cov=nexus                # Coverage report
pytest --cov=nexus --cov-report=html   # HTML coverage
pytest tests/test_waypoint.py      # Specific file
pytest tests/test_waypoint.py::TestWaypoint::test_waypoint_creation  # Specific test
pytest -k "hash"                   # Tests matching keyword
pytest -m "not slow"               # Skip slow tests
```

### Continuous Testing

```bash
pytest --looponfail    # Re-run on file changes (requires pytest-watch)
pytest -x              # Stop on first failure
```

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── test_waypoint.py           # Waypoint tests
├── test_blockchain.py         # IPFS/blockchain tests
├── test_recorder.py           # Recording tests (future)
├── test_playback.py           # Playback tests (future)
└── test_cli.py                # CLI tests (future)
```

## Test Coverage

Current coverage targets:

- Core modules: 90%+ coverage
- Critical paths: 100% coverage
- Optional features: 70%+ coverage

Check coverage:

```bash
pytest --cov=nexus --cov-report=term-missing
pytest --cov=nexus --cov-report=html   # Generate HTML report
```

## Writing Tests

### Basic Test Structure

```python
"""
Tests for module_name.

Clear description of what this test file covers.
"""

import pytest
from nexus import YourClass


class TestYourClass:
    """Tests for YourClass."""

    def test_creation(self):
        """Test basic instantiation."""
        obj = YourClass()
        assert obj is not None

    def test_with_args(self):
        """Test with arguments."""
        obj = YourClass(param='value')
        assert obj.param == 'value'

    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ValueError):
            YourClass(invalid_param=True)
```

### Using Fixtures

```python
@pytest.fixture
def sample_waypoint():
    """Provide a sample waypoint for tests."""
    from nexus import Waypoint
    waypoint = Waypoint(url='https://example.com')
    waypoint.add_action(ActionType.CLICK, selector='#button')
    return waypoint


def test_with_fixture(sample_waypoint):
    """Test using a fixture."""
    assert sample_waypoint.url == 'https://example.com'
    assert len(sample_waypoint.actions) == 1
```

### Mocking External Services

```python
from unittest.mock import patch, Mock

@patch('requests.post')
def test_ipfs_upload(mock_post):
    """Test IPFS upload with mocked requests."""
    mock_response = Mock()
    mock_response.json.return_value = {'IpfsHash': 'QmTest123'}
    mock_post.return_value = mock_response

    blockchain = IPFSBlockchain(api_key='test', api_secret='test')
    waypoint = Waypoint(url='https://example.com')

    ipfs_hash = blockchain.store_waypoint(waypoint)

    assert ipfs_hash == 'QmTest123'
    mock_post.assert_called_once()
```

### Async Tests

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result is not None
```

## Test Categories

### Unit Tests

Fast, isolated tests of single functions/classes:

```python
def test_waypoint_hash():
    """Unit test: hash computation."""
    wp1 = Waypoint(url='https://a.com')
    wp2 = Waypoint(url='https://a.com')
    assert wp1.compute_hash() == wp2.compute_hash()
```

### Integration Tests

Tests that verify components work together:

```python
@patch('requests.get')
def test_retrieve_and_replay(mock_get):
    """Integration: retrieve waypoint and replay it."""
    # Mock IPFS retrieval
    waypoint = create_sample_waypoint()
    # Test playback with retrieved waypoint
    ...
```

### Fixtures (conftest.py)

Available fixtures for all tests:

```python
@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files."""
    return tmp_path

@pytest.fixture
def sample_waypoint_json():
    """Sample waypoint JSON string."""
    return """{"url": "https://example.com", ...}"""

@pytest.fixture
def mock_pinata_key():
    """Mock Pinata API key."""
    return "test_key_123"
```

## Common Patterns

### Testing Exceptions

```python
def test_missing_url():
    """Test exception on missing URL."""
    with pytest.raises(ValueError, match="URL required"):
        Waypoint()  # Missing required url parameter
```

### Testing with Parametrize

```python
@pytest.mark.parametrize("action_type,selector", [
    (ActionType.CLICK, "#button"),
    (ActionType.TYPE, "#input"),
    (ActionType.SCROLL, None),
])
def test_action_creation(action_type, selector):
    """Test various action types."""
    action = WaypointAction(action_type=action_type, selector=selector)
    assert action.action_type == action_type
```

### Testing State Changes

```python
def test_waypoint_mutation():
    """Test waypoint state changes."""
    waypoint = Waypoint(url='https://example.com')
    assert len(waypoint.actions) == 0

    waypoint.add_action(ActionType.CLICK, selector='#button')
    assert len(waypoint.actions) == 1

    waypoint.add_action(ActionType.TYPE, selector='#input', value='text')
    assert len(waypoint.actions) == 2
```

## Debugging Tests

### Print Debugging

```python
def test_with_debug_output(capsys):
    """Test with debug output capture."""
    print("Debug info here")
    captured = capsys.readouterr()
    assert "Debug info here" in captured.out
```

### Breakpoints

```python
def test_with_breakpoint():
    """Test with interactive debugging."""
    result = some_function()
    breakpoint()  # Execution pauses here
    assert result is correct
```

### Verbose Output

```bash
pytest -vv                    # Extra verbose
pytest -vv --tb=long         # Detailed tracebacks
pytest --showlocals           # Show local variables on failure
```

## CI/CD Testing

Tests run automatically on:

- Every push to `main` or `develop`
- Every pull request
- Multiple Python versions (3.9, 3.10, 3.11, 3.12)

See `.github/workflows/ci.yml` for details.

## Performance Testing

For slow tests, mark them:

```python
@pytest.mark.slow
def test_full_browser_session():
    """Test that takes >5 seconds."""
    ...
```

Skip slow tests:

```bash
pytest -m "not slow"
```

## Troubleshooting

### Tests Pass Locally but Fail in CI

- Check Python version differences
- Verify environment variables are set
- Check for timing-dependent tests
- Review mocking setup

### Flaky Tests

Tests that fail intermittently:

```python
@pytest.mark.flaky(reruns=3)  # Retry up to 3 times
def test_occasionally_fails():
    """Test that might fail due to timing."""
    ...
```

### Import Errors

Ensure test dependencies are installed:

```bash
pip install -e ".[dev]"
pytest
```

## Best Practices

1. **Descriptive Names** - Test names clearly describe what they test
2. **Arrange-Act-Assert** - Organize tests with setup, action, verification
3. **Single Responsibility** - Each test verifies one thing
4. **Mock External Dependencies** - Don't hit real APIs in tests
5. **Use Fixtures** - DRY up common test setup
6. **Fast Tests** - Aim for tests under 100ms
7. **Deterministic** - Tests should always produce same result
8. **Isolated** - Tests shouldn't depend on other tests

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

Questions? Open an issue on GitHub or contact nattimmis@gmail.com
