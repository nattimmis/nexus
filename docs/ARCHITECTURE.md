# Nexus Architecture

High-level overview of Nexus system design and components.

## System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nexus System                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐              ┌──────────────────┐        │
│  │   CLI (click)    │              │  API (Direct)    │        │
│  │  - record        │              │  - Record        │        │
│  │  - replay        │              │  - Replay        │        │
│  │  - upload        │              │  - Verify        │        │
│  │  - verify        │              │  - Store         │        │
│  └────────┬─────────┘              └────────┬─────────┘        │
│           │                                  │                  │
│           └──────────────┬───────────────────┘                 │
│                          │                                      │
│                   ┌──────▼──────┐                              │
│                   │  Waypoint   │                              │
│                   │  Manager    │                              │
│                   └──────┬──────┘                              │
│                          │                                      │
│        ┌─────────────────┼─────────────────┐                  │
│        │                 │                 │                  │
│   ┌────▼────┐      ┌─────▼──────┐   ┌─────▼──────┐           │
│   │ Recorder │      │  Playback  │   │ Blockchain │           │
│   │          │      │  Engine    │   │  (IPFS)    │           │
│   └────┬─────┘      └─────┬──────┘   └─────┬──────┘           │
│        │                  │                │                  │
│   ┌────▼─────────┐   ┌────▼──────┐   ┌────▼──────┐           │
│   │ Playwright   │   │ Waypoint  │   │  Pinata   │           │
│   │ Browser      │   │ Executor  │   │    API    │           │
│   └──────────────┘   └───────────┘   └──────────┘           │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. Waypoint (`waypoint.py`)

**Purpose:** Data structures for recording navigation sequences.

**Key Classes:**
- `Waypoint` - Complete navigation recording
- `WaypointAction` - Individual action (click, type, navigate, etc.)
- `WaypointAssertion` - Assertion to verify during playback
- `ActionType` - Enumeration of action types
- `AssertionType` - Enumeration of assertion types

**Features:**
- Pydantic-based validation
- JSON serialization/deserialization
- SHA-256 hashing for integrity
- Version tracking for compatibility

**Data Flow:**
```
Recorded Actions → JSON Serialization → Hash Computation → IPFS Upload
```

### 2. Recorder (`recorder.py`)

**Purpose:** Record user interactions on web pages using Playwright.

**Key Classes:**
- `NavigationRecorder` - Main recording interface
- `InteractiveRecorder` - Interactive step-by-step recording

**Features:**
- Async Playwright integration
- Event listener for page interactions
- Action recording with timestamps
- Assertion definition API

**Workflow:**
```
Start Browser → Navigate URL → Listen Events → Record Actions → Stop & Save
```

### 3. Blockchain (`blockchain.py`)

**Purpose:** IPFS integration for immutable waypoint storage.

**Key Class:**
- `IPFSBlockchain` - IPFS storage and retrieval via Pinata API

**Features:**
- Pinata API integration
- JSON upload with metadata
- Content retrieval via public gateway
- Pin management (pin/unpin/list)
- Hash verification

**API Interactions:**
```
Local Waypoint → Pinata Upload → IPFS Hash → Store Hash Locally
     ↓
   Later: IPFS Hash → Pinata Gateway → Retrieve JSON → Waypoint Object
```

### 4. Playback (`playback.py`)

**Purpose:** Deterministic replay of recorded waypoints.

**Key Classes:**
- `NavigationPlayback` - Main replay engine
- `PlaybackError` - Playback-specific exceptions
- `AssertionFailedError` - Assertion verification failures

**Features:**
- Async execution of recorded actions
- Assertion verification during replay
- Strict and lenient modes
- Comprehensive error handling

**Execution Flow:**
```
Load Waypoint → Open Browser → Execute Actions → Verify Assertions → Report
```

### 5. CLI (`cli.py`)

**Purpose:** Command-line interface for Nexus operations.

**Commands:**
- `nexus record` - Interactive recording
- `nexus replay` - Playback from IPFS
- `nexus upload` - Upload waypoint to IPFS
- `nexus verify` - Verify waypoint integrity
- `nexus list-pins` - List pinned waypoints

**Architecture:**
- Click framework for command structure
- Async execution with asyncio
- Comprehensive error handling and user feedback

## Data Flow

### Recording Flow

```
User Action → Playwright Event → Recorder Captures
                                     ↓
                            WaypointAction/Assertion
                                     ↓
                              Waypoint Object
                                     ↓
                           JSON Serialization
                                     ↓
                        SHA-256 Hash Computation
                                     ↓
                           Local File Save
                                     ↓
                      Optional: IPFS Upload via Pinata
```

### Playback Flow

```
IPFS Hash / Local File
         ↓
  Waypoint Deserialization
         ↓
   Browser Launch (Playwright)
         ↓
   Action Execution Loop
   - Click
   - Type
   - Navigate
   - Wait
   - Screenshot
         ↓
   Assertion Verification Loop
   - Text Present
   - Element Visible
   - URL Matches
   - Title Contains
         ↓
    Results & Reporting
```

## Technology Stack

### Browser Automation
- **Playwright** - Cross-browser automation (Chromium, Firefox, WebKit)
- **async/await** - Asynchronous operations for performance

### Data Structures
- **Pydantic** - Runtime validation and serialization
- **JSON** - Human-readable, widely supported format

### Storage
- **IPFS** - Decentralized, immutable content addressing
- **Pinata API** - Reliable IPFS pinning service

### CLI
- **Click** - Modern command-line framework
- **Logging** - Python standard logging with custom formatting

### Testing
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **unittest.mock** - Test mocking and patching

## Module Dependencies

```
┌─────────────────────────────────────────┐
│         External Dependencies           │
├─────────────────────────────────────────┤
│ playwright  pydantic  click  requests    │
│ python-dotenv  aiohttp                  │
└─────────────────────────────────────────┘
         ↑              ↑              ↑
         │              │              │
    ┌────┴──┐   ┌──────┴──────┐  ┌────┴──┐
    │        │   │             │  │       │
  recorder blockchain         cli playback
    │        │   │             │  │       │
    └────┬───┴───┴─────────────┴──┴───┬───┘
         │                            │
         └────────────┬───────────────┘
                      │
                  waypoint
                      │
                logging_util
```

## Error Handling

### Levels of Error Handling

1. **Input Validation** - Pydantic models validate data on creation
2. **Network Errors** - IPFS upload/retrieval with retries and timeouts
3. **Browser Errors** - Playwright timeout handling and element not found
4. **Assertion Errors** - Strict vs lenient modes for playback failures
5. **File Operations** - JSON serialization error handling

### Error Categories

- `ValueError` - Invalid input or missing required fields
- `requests.RequestException` - Network/API errors
- `PlaybackError` - Playback execution failures
- `AssertionFailedError` - Assertion verification failures
- `ElementNotFoundError` - Element not found during playback

## Scalability Considerations

1. **Async Operations** - Non-blocking I/O for network and browser operations
2. **IPFS Storage** - Decentralized, no central server bottleneck
3. **Pinata Pinning** - High availability with global CDN
4. **Stateless Design** - Each operation is independent
5. **Batch Operations** - Support for replaying multiple waypoints

## Security Considerations

1. **Content Immutability** - SHA-256 hashing ensures content integrity
2. **API Credentials** - Environment variables keep secrets out of code
3. **Public IPFS** - Don't store sensitive data (passwords, keys, PII)
4. **HTTPS** - Pinata gateway uses HTTPS for content delivery
5. **No Execution** - Recorded content is data, not executable code

## Future Enhancements

1. **Multi-browser Support** - Firefox, Safari, Edge
2. **Local IPFS Node** - Option for private/offline storage
3. **Waypoint Composition** - Combine multiple waypoints into workflows
4. **Advanced Selectors** - XPath, image recognition, ML-based selection
5. **Performance Metrics** - Timing analysis and bottleneck detection
6. **Database Backend** - PostgreSQL for waypoint versioning and metadata
7. **Browser Extension** - 1-click recording from browser UI

---

For more information, see [README.md](../README.md) and [TESTING.md](../TESTING.md)
