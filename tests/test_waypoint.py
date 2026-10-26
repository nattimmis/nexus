"""
Tests for Nexus waypoint module.
"""

import pytest
import json
from datetime import datetime
from nexus.waypoint import (
    Waypoint,
    WaypointAction,
    WaypointAssertion,
    ActionType,
    AssertionType,
)


class TestWaypointAction:
    """Tests for WaypointAction class."""

    def test_action_creation(self):
        """Test creating a waypoint action."""
        action = WaypointAction(
            action_type=ActionType.CLICK,
            selector='#submit',
        )
        assert action.action_type == ActionType.CLICK
        assert action.selector == '#submit'

    def test_action_with_value(self):
        """Test action with value."""
        action = WaypointAction(
            action_type=ActionType.TYPE,
            selector='#email',
            value='test@example.com',
        )
        assert action.action_type == ActionType.TYPE
        assert action.value == 'test@example.com'

    def test_action_timeout(self):
        """Test action timeout."""
        action = WaypointAction(
            action_type=ActionType.CLICK,
            selector='#button',
            timeout=5.0,
        )
        assert action.timeout == 5.0


class TestWaypointAssertion:
    """Tests for WaypointAssertion class."""

    def test_assertion_creation(self):
        """Test creating a waypoint assertion."""
        assertion = WaypointAssertion(
            assertion_type=AssertionType.TEXT_PRESENT,
            target='Welcome',
        )
        assert assertion.assertion_type == AssertionType.TEXT_PRESENT
        assert assertion.target == 'Welcome'

    def test_assertion_with_expected(self):
        """Test assertion with expected value."""
        assertion = WaypointAssertion(
            assertion_type=AssertionType.VALUE_EQUALS,
            target='#email',
            expected='test@example.com',
        )
        assert assertion.expected == 'test@example.com'


class TestWaypoint:
    """Tests for Waypoint class."""

    def test_waypoint_creation(self):
        """Test creating a waypoint."""
        waypoint = Waypoint(url='https://example.com')
        assert waypoint.url == 'https://example.com'
        assert len(waypoint.actions) == 0
        assert len(waypoint.assertions) == 0

    def test_waypoint_to_dict(self):
        """Test converting waypoint to dictionary."""
        waypoint = Waypoint(url='https://example.com', description='Test')
        waypoint.add_action(ActionType.CLICK, selector='#button')

        data = waypoint.to_dict()
        assert data['url'] == 'https://example.com'
        assert data['description'] == 'Test'
        assert len(data['actions']) == 1

    def test_waypoint_hash_computation(self):
        """Test waypoint hash computation."""
        waypoint1 = Waypoint(url='https://example.com')
        waypoint1.add_action(ActionType.CLICK, selector='#button')
        hash1 = waypoint1.compute_hash()

        waypoint2 = Waypoint(url='https://example.com')
        waypoint2.add_action(ActionType.CLICK, selector='#button')
        hash2 = waypoint2.compute_hash()

        # Same content should produce same hash
        assert hash1 == hash2

    def test_waypoint_hash_differs_on_change(self):
        """Test that hash changes when content changes."""
        waypoint = Waypoint(url='https://example.com')
        hash1 = waypoint.compute_hash()

        waypoint.add_action(ActionType.CLICK, selector='#button')
        hash2 = waypoint.compute_hash()

        # Different content should produce different hash
        assert hash1 != hash2

    def test_waypoint_to_json(self):
        """Test converting waypoint to JSON."""
        waypoint = Waypoint(url='https://example.com')
        waypoint.add_action(ActionType.CLICK, selector='#button')

        json_str = waypoint.to_json()
        data = json.loads(json_str)

        assert data['url'] == 'https://example.com'
        assert len(data['actions']) == 1

    def test_waypoint_from_json(self, sample_waypoint_json):
        """Test deserializing waypoint from JSON."""
        waypoint = Waypoint.from_json(sample_waypoint_json)

        assert waypoint.url == 'https://example.com'
        assert len(waypoint.actions) == 2
        assert len(waypoint.assertions) == 1
        assert waypoint.description == 'Test navigation'

    def test_waypoint_json_round_trip(self):
        """Test JSON serialization round-trip."""
        original = Waypoint(
            url='https://example.com',
            description='Test',
        )
        original.add_action(ActionType.CLICK, selector='#button')
        original.add_assertion(AssertionType.TEXT_PRESENT, target='Success')

        json_str = original.to_json()
        restored = Waypoint.from_json(json_str)

        assert restored.url == original.url
        assert restored.description == original.description
        assert len(restored.actions) == len(original.actions)
        assert len(restored.assertions) == len(original.assertions)

    def test_waypoint_add_action(self):
        """Test adding actions to waypoint."""
        waypoint = Waypoint(url='https://example.com')

        waypoint.add_action(ActionType.CLICK, selector='#button')
        assert len(waypoint.actions) == 1

        waypoint.add_action(ActionType.TYPE, selector='#input', value='text')
        assert len(waypoint.actions) == 2

    def test_waypoint_add_assertion(self):
        """Test adding assertions to waypoint."""
        waypoint = Waypoint(url='https://example.com')

        waypoint.add_assertion(AssertionType.TEXT_PRESENT, target='Welcome')
        assert len(waypoint.assertions) == 1

        waypoint.add_assertion(
            AssertionType.ELEMENT_VISIBLE,
            target='#success',
        )
        assert len(waypoint.assertions) == 2

    def test_waypoint_verify_hash(self):
        """Test waypoint hash verification."""
        waypoint = Waypoint(url='https://example.com')
        waypoint.add_action(ActionType.CLICK, selector='#button')

        correct_hash = waypoint.compute_hash()
        assert waypoint.verify_hash(correct_hash) is True

        wrong_hash = 'invalid_hash_123'
        assert waypoint.verify_hash(wrong_hash) is False

    def test_waypoint_update_hash(self):
        """Test updating waypoint hash."""
        waypoint = Waypoint(url='https://example.com')
        waypoint.update_hash()

        assert len(waypoint.hash) == 64  # SHA-256 hex is 64 chars
        assert waypoint.verify_hash(waypoint.hash) is True


class TestActionType:
    """Tests for ActionType enum."""

    def test_action_type_values(self):
        """Test action type enum values."""
        assert ActionType.CLICK == 'click'
        assert ActionType.DOUBLE_CLICK == 'double_click'
        assert ActionType.TYPE == 'type'
        assert ActionType.SELECT == 'select'
        assert ActionType.HOVER == 'hover'
        assert ActionType.SCROLL == 'scroll'
        assert ActionType.NAVIGATE == 'navigate'
        assert ActionType.WAIT == 'wait'


class TestAssertionType:
    """Tests for AssertionType enum."""

    def test_assertion_type_values(self):
        """Test assertion type enum values."""
        assert AssertionType.TEXT_PRESENT == 'text_present'
        assert AssertionType.ELEMENT_VISIBLE == 'element_visible'
        assert AssertionType.ELEMENT_HIDDEN == 'element_hidden'
        assert AssertionType.URL_MATCHES == 'url_matches'
        assert AssertionType.TITLE_CONTAINS == 'title_contains'
        assert AssertionType.VALUE_EQUALS == 'value_equals'
