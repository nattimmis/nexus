"""
Pytest configuration and fixtures.
"""

import pytest
import os
from pathlib import Path


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_waypoint_json():
    """Provide sample waypoint JSON for testing."""
    return """{
  "url": "https://example.com",
  "actions": [
    {
      "action_type": "navigate",
      "selector": null,
      "value": "https://example.com",
      "timeout": 10.0,
      "timestamp": "2024-01-01T00:00:00"
    },
    {
      "action_type": "click",
      "selector": "#submit-button",
      "value": null,
      "timeout": 10.0,
      "timestamp": "2024-01-01T00:00:01"
    }
  ],
  "assertions": [
    {
      "assertion_type": "text_present",
      "target": "Welcome",
      "expected": null,
      "timestamp": "2024-01-01T00:00:02"
    }
  ],
  "description": "Test navigation",
  "version": "1.0",
  "created_at": "2024-01-01T00:00:00"
}"""


@pytest.fixture(scope="session")
def mock_pinata_key():
    """Provide a mock Pinata API key for testing."""
    return "test_pinata_key_123456"


@pytest.fixture(scope="session")
def mock_pinata_secret():
    """Provide a mock Pinata API secret for testing."""
    return "test_pinata_secret_123456"
