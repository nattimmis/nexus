# Changelog

All notable changes to Nexus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure and core modules
- Waypoint data structures with JSON serialization
- Playwright-based navigation recorder
- IPFS integration via Pinata API
- Playback engine with assertion verification
- CLI with full command support
- Comprehensive test suite
- GitHub Actions CI/CD pipeline
- Complete documentation and examples

### Planned
- Browser extension for 1-click recording
- Support for Firefox, Safari, and Edge browsers
- Local IPFS node option
- Waypoint versioning and merging
- Multi-step workflow composition
- Advanced selectors (XPath, image recognition)
- Performance metrics and analytics
- Database backend for waypoint history

## [0.1.0] - 2024-01-15

### Initial Release

First release of Nexus with core functionality:

#### Added
- Full Playwright integration for web browser automation
- Waypoint recording with action and assertion support
- IPFS storage via Pinata API
- SHA-256 hash verification for integrity
- Interactive CLI for recording and replaying
- Async playback engine with strict/lenient assertion modes
- Complete type hints and comprehensive error handling
- Production-ready logging throughout
- Full test suite with 90%+ coverage
- Complete API documentation and examples
- GitHub Actions CI/CD with automatic PyPI publishing
- Apache 2.0 license

### Features

#### Recording
- Interactive recording mode with real-time command feedback
- Support for clicks, typing, selections, navigation, waits
- Automatic action timestamp recording
- Custom assertion definitions
- Waypoint hashing for integrity

#### Storage
- IPFS-based immutable storage
- Pinata API integration for reliable pinning
- Public gateway access via HTTP
- Pin management (pin/unpin/list)

#### Playback
- Deterministic replay of recorded sequences
- Assertion verification during playback
- Headless and headed browser modes
- Strict and lenient assertion modes
- Comprehensive error handling and logging

#### CLI
- `nexus record <url>` - Interactive recording
- `nexus replay <ipfs_hash>` - Replay from IPFS
- `nexus upload <file>` - Upload waypoint to IPFS
- `nexus verify <ipfs_hash>` - Verify waypoint integrity
- `nexus list-pins` - List pinned waypoints
- Logging level control via `--log-level` flag

### Documentation
- Comprehensive README with quick start
- API documentation for all modules
- Complete examples for recording and replaying
- Contributing guidelines
- License and security considerations

### Testing
- Waypoint encoding/decoding tests
- Hash computation and verification tests
- IPFS integration tests (mocked)
- Action execution tests
- Assertion verification tests
- CLI command tests

---

[Unreleased]: https://github.com/nattimmis/nexus/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nattimmis/nexus/releases/tag/v0.1.0
