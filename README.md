# Nexus: Record and Replay Web Navigation on Blockchain

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Nexus is an open-source tool that records web navigation sequences via Playwright and stores them immutably on IPFS (InterPlanetary File System). Perfect for automation testing, web scraping, and creating permanent records of complex user journeys.

## Why Nexus?

- **Record Once, Replay Anywhere** - Capture complex navigation sequences and replay them deterministically
- **Blockchain Immutability** - Store waypoints on IPFS for permanent, tamper-proof records
- **Zero Server Cost** - Use Pinata's public IPFS gateway or run your own IPFS node
- **Type-Safe** - Full type hints and Pydantic models for data integrity
- **Production Ready** - Comprehensive error handling, logging, and unit tests
- **CLI First** - Simple command-line interface for recording and replaying

## Features

- **Interactive Recording** - Record navigation with real-time command feedback
- **Waypoint Format** - JSON-serialized navigation steps with SHA-256 hashing
- **Assertion Verification** - Assert text presence, element visibility, URLs, and more
- **IPFS Storage** - Store waypoints immutably on decentralized IPFS network
- **Integrity Verification** - Hash-based verification of waypoint authenticity
- **Pinning Management** - Keep waypoints alive with explicit pinning control
- **Async Playback** - Fast, parallel replay engine with strict/lenient modes

## Installation

### Via pip (Coming Soon)

```bash
pip install nexus-autopaths
```

### From Source

```bash
git clone https://github.com/nattimmis/nexus.git
cd nexus
pip install -e .
```

### For Development

```bash
pip install -e ".[dev]"
pytest
```

## Quick Start

### 1. Set Up IPFS Credentials

Get free Pinata API credentials at [https://pinata.cloud](https://pinata.cloud):

```bash
export PINATA_API_KEY="your_api_key_here"
export PINATA_API_SECRET="your_api_secret_here"
```

Or store in `.env`:

```bash
PINATA_API_KEY=your_api_key_here
PINATA_API_SECRET=your_api_secret_here
```

### 2. Record Navigation

```bash
nexus record https://example.com
```

Interactive commands:
- `c <selector>` - Click element (e.g., `c #submit-button`)
- `t <selector> <text>` - Type text (e.g., `t #email user@example.com`)
- `s <selector> <value>` - Select dropdown (e.g., `s #country USA`)
- `w <seconds>` - Wait (e.g., `w 2`)
- `a text <text>` - Assert text present (e.g., `a text "Success"`)
- `a element <selector>` - Assert element visible (e.g., `a element #success`)
- `a url <pattern>` - Assert URL matches (e.g., `a url dashboard`)
- `screenshot <filename>` - Take screenshot
- `done` - Finish recording

### 3. Save Waypoint

```bash
nexus record https://example.com -o my_navigation.json -d "Login flow test"
```

### 4. Upload to IPFS

```bash
nexus upload my_navigation.json
```

Response:
```
Upload successful!
IPFS Hash: QmXxxx...

To replay this waypoint:
  nexus replay QmXxxx...
```

### 5. Replay Waypoint

```bash
nexus replay QmXxxx...
```

### 6. Verify Integrity

```bash
nexus verify QmXxxx...
```

## API Usage

### Recording Programmatically

```python
import asyncio
from nexus import NavigationRecorder

async def record_login():
    recorder = NavigationRecorder()
    await recorder.start_recording('https://example.com/login', headless=False)
    
    # Record actions
    await recorder.record_click('#email-input')
    await recorder.record_type('#email-input', 'user@example.com')
    await recorder.record_click('#password-input')
    await recorder.record_type('#password-input', 'password123')
    await recorder.record_click('#login-button')
    await recorder.record_wait(2.0)
    await recorder.record_assertion_text_present('Dashboard')
    
    waypoint = await recorder.stop_recording()
    return waypoint

waypoint = asyncio.run(record_login())
print(f"Recorded waypoint: {waypoint.hash}")
```

### Replaying Programmatically

```python
import asyncio
from nexus import NavigationPlayback, IPFSBlockchain

async def replay():
    blockchain = IPFSBlockchain()
    waypoint = blockchain.retrieve_waypoint('QmXxxx...')
    
    playback = NavigationPlayback(strict_assertions=True)
    success = await playback.replay_waypoint(waypoint, headless=True)
    
    return success

success = asyncio.run(replay())
print(f"Replay success: {success}")
```

### Verifying Waypoints

```python
from nexus import IPFSBlockchain, Waypoint

blockchain = IPFSBlockchain()
waypoint = blockchain.retrieve_waypoint('QmXxxx...')

# Verify integrity
is_valid = blockchain.verify_waypoint_integrity('QmXxxx...', waypoint.hash)
print(f"Valid: {is_valid}")
```

## Waypoint Format

Waypoints are stored as JSON with complete navigation metadata:

```json
{
  "url": "https://example.com",
  "actions": [
    {
      "action_type": "click",
      "selector": "#submit-button",
      "value": null,
      "timeout": 10.0,
      "timestamp": "2024-01-15T10:30:45.123456"
    },
    {
      "action_type": "type",
      "selector": "#email",
      "value": "user@example.com",
      "timeout": 10.0,
      "timestamp": "2024-01-15T10:30:46.234567"
    }
  ],
  "assertions": [
    {
      "assertion_type": "text_present",
      "target": "Welcome",
      "expected": null,
      "timestamp": "2024-01-15T10:30:47.345678"
    },
    {
      "assertion_type": "url_matches",
      "target": "dashboard",
      "expected": null,
      "timestamp": "2024-01-15T10:30:48.456789"
    }
  ],
  "description": "User login flow",
  "version": "1.0",
  "created_at": "2024-01-15T10:30:45"
}
```

## Action Types

- `click` - Click an element
- `double_click` - Double-click an element
- `type` - Type text into an element
- `select` - Select option in dropdown
- `hover` - Hover over an element
- `scroll` - Scroll page (up/down)
- `navigate` - Navigate to URL
- `wait` - Wait N seconds
- `screenshot` - Take screenshot

## Assertion Types

- `text_present` - Assert text is visible on page
- `element_visible` - Assert element is visible
- `element_hidden` - Assert element is hidden
- `url_matches` - Assert URL contains pattern
- `title_contains` - Assert page title contains text
- `value_equals` - Assert input value equals expected

## Architecture

### Core Modules

- **waypoint.py** - Data models and JSON serialization
- **blockchain.py** - IPFS integration via Pinata API
- **recorder.py** - Playwright-based navigation recording
- **playback.py** - Replay engine with assertion verification
- **cli.py** - Click-based command-line interface
- **logging_util.py** - Centralized logging utilities

### Design Decisions

1. **IPFS over Blockchain** - No transaction fees, instant storage, perfect for immutable records
2. **Pinata API** - Reliable pinning without running full IPFS node
3. **JSON Format** - Human-readable, easy to debug, widely supported
4. **SHA-256 Hashing** - Industry standard integrity verification
5. **Async Playback** - Fast, non-blocking execution
6. **Pydantic Models** - Runtime type validation and serialization

## Configuration

### Environment Variables

```bash
PINATA_API_KEY=your_api_key
PINATA_API_SECRET=your_api_secret
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### CLI Options

```bash
nexus --log-level DEBUG record https://example.com
nexus --log-level INFO replay QmXxxx...
nexus --log-level WARNING verify QmXxxx...
```

## Examples

See the `examples/` directory for complete runnable examples:

- `examples/record_example.py` - Recording a login flow
- `examples/replay_example.py` - Replaying a stored waypoint
- `examples/assertion_example.py` - Advanced assertion patterns

## Testing

Run the full test suite:

```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest --cov                    # With coverage
pytest tests/test_waypoint.py   # Specific test file
```

Test coverage includes:
- Waypoint creation and hashing
- JSON serialization/deserialization
- IPFS upload/retrieval (mocked)
- Action execution and assertion verification
- CLI command handling

## Contributing

Contributions welcome! Please follow:

1. Code style: Black (100 char line length)
2. Type hints: Full coverage with mypy
3. Tests: 90%+ coverage required
4. Docstrings: Every function must have one
5. Commits: Clear, atomic, signed preferred

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Roadmap

- [ ] Support for other browsers (Firefox, Safari, Edge)
- [ ] Local IPFS node option
- [ ] Waypoint versioning and merging
- [ ] Multi-step workflow composition
- [ ] Browser extension for 1-click recording
- [ ] Database backend for waypoint history
- [ ] Advanced selectors (XPath, image recognition)
- [ ] Performance metrics and analytics

## Security Considerations

1. **IPFS Content** - All content is public; don't store sensitive data
2. **API Credentials** - Keep Pinata keys secure in environment variables
3. **Browser Data** - Clear local storage/cookies before recording sensitive flows
4. **Hash Verification** - Always verify waypoint integrity before replay

## Support

- GitHub Issues: [github.com/nattimmis/nexus/issues](https://github.com/nattimmis/nexus/issues)
- Discussions: [github.com/nattimmis/nexus/discussions](https://github.com/nattimmis/nexus/discussions)
- Email: nattimmis@gmail.com

## Related Projects

- [Playwright](https://playwright.dev) - Browser automation framework
- [IPFS](https://ipfs.io) - InterPlanetary File System
- [Pinata](https://pinata.cloud) - IPFS pinning service
- [Pydantic](https://pydantic-docs.helpmanual.io) - Data validation library

---

Built with passion for robust, decentralized testing automation.
