"""
Waypoint data structures and encoding/decoding for Nexus navigation recording.

Waypoints are atomic units of navigation: clicks, text input, page waits, assertions.
Each waypoint is encoded as JSON and hashed for integrity verification.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from nexus.selectors import SelectorChain


class ActionType(str, Enum):
    """Types of navigation actions."""
    CLICK = 'click'
    DOUBLE_CLICK = 'double_click'
    TYPE = 'type'
    SELECT = 'select'
    HOVER = 'hover'
    SCROLL = 'scroll'
    FILL_FORM = 'fill_form'
    NAVIGATE = 'navigate'
    WAIT = 'wait'
    SCREENSHOT = 'screenshot'


class AssertionType(str, Enum):
    """Types of assertions to verify during replay."""
    TEXT_PRESENT = 'text_present'
    ELEMENT_VISIBLE = 'element_visible'
    ELEMENT_HIDDEN = 'element_hidden'
    URL_MATCHES = 'url_matches'
    TITLE_CONTAINS = 'title_contains'
    VALUE_EQUALS = 'value_equals'


class WaypointAction(BaseModel):
    """
    Represents a single action in navigation.

    Attributes:
        action_type: Type of action (click, type, navigate, etc.).
        selector: CSS/XPath selector for the target element (optional).
        selector_chain: Multi-candidate selector chain with fallbacks (optional).
        value: Value for type/fill actions (optional).
        form_fields: Dict of selectors to values for FILL_FORM actions (optional).
        timeout: Maximum time to wait for action (seconds).
        timestamp: When the action was recorded.
    """
    action_type: ActionType
    selector: Optional[str] = None
    selector_chain: Optional[SelectorChain] = None
    value: Optional[str] = None
    form_fields: Optional[Dict[str, str]] = None
    timeout: float = 10.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = False


class WaypointAssertion(BaseModel):
    """
    Represents an assertion to verify during replay.

    Attributes:
        assertion_type: Type of assertion (text_present, element_visible, etc.).
        target: What to assert (text, element selector, URL pattern, etc.).
        expected: Expected value (optional).
        timestamp: When the assertion was recorded.
    """
    assertion_type: AssertionType
    target: str
    expected: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = False


class Waypoint(BaseModel):
    """
    Complete waypoint record: actions and assertions for a navigation sequence.

    Attributes:
        id: Unique waypoint identifier (hash-based).
        url: URL where the waypoint was recorded.
        actions: List of actions performed.
        assertions: List of assertions to verify.
        description: Human-readable description.
        version: Waypoint format version (kept as '1.0' for backward-compat).
        parent_hash: SHA-256 hash of parent waypoint in version chain (optional).
        chain_version: Version number in the chain (for tracking revisions).
        created_at: Timestamp when waypoint was created.
        hash: SHA-256 hash of waypoint content (for integrity).
        ipfs_hash: IPFS hash if stored on blockchain.
    """
    id: str = Field(default='')
    url: str
    actions: List[WaypointAction] = Field(default_factory=list)
    assertions: List[WaypointAssertion] = Field(default_factory=list)
    description: str = ''
    version: str = '1.0'
    parent_hash: Optional[str] = None
    chain_version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    hash: str = ''
    ipfs_hash: Optional[str] = None

    class Config:
        use_enum_values = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert waypoint to dictionary (for hashing and JSON serialization).

        New fields (selector_chain, parent_hash, chain_version, form_fields)
        are only emitted when non-default, preserving hash stability for
        existing pinned waypoints.

        Returns:
            Dictionary representation with serialized timestamps.
        """
        result = {
            'url': self.url,
            'actions': [],
            'assertions': [
                {
                    'assertion_type': a.assertion_type,
                    'target': a.target,
                    'expected': a.expected,
                    'timestamp': a.timestamp.isoformat(),
                }
                for a in self.assertions
            ],
            'description': self.description,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
        }

        for a in self.actions:
            action_dict = {
                'action_type': a.action_type,
                'selector': a.selector,
                'value': a.value,
                'timeout': a.timeout,
                'timestamp': a.timestamp.isoformat(),
            }
            if a.selector_chain is not None and a.selector_chain.candidates:
                action_dict['selector_chain'] = a.selector_chain.model_dump(mode='json')
            if a.form_fields is not None:
                action_dict['form_fields'] = a.form_fields
            result['actions'].append(action_dict)

        if self.parent_hash is not None:
            result['parent_hash'] = self.parent_hash
        if self.chain_version != 1:
            result['chain_version'] = self.chain_version

        return result

    def compute_hash(self) -> str:
        """
        Compute SHA-256 hash of waypoint content for integrity verification.

        Returns:
            Hex-encoded SHA-256 hash.
        """
        content = json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content.encode()).hexdigest()

    def update_hash(self) -> None:
        """Compute and store the hash."""
        self.hash = self.compute_hash()

    def to_json(self) -> str:
        """
        Serialize waypoint to JSON string.

        Returns:
            JSON representation of waypoint.
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Waypoint':
        """
        Deserialize waypoint from JSON string.

        Args:
            json_str: JSON representation of waypoint.

        Returns:
            Waypoint instance.

        Raises:
            json.JSONDecodeError: If JSON is invalid.
            ValueError: If required fields are missing.
        """
        data = json.loads(json_str)

        actions = []
        for a in data.get('actions', []):
            action = WaypointAction(
                action_type=a['action_type'],
                selector=a.get('selector'),
                value=a.get('value'),
                timeout=a.get('timeout', 10.0),
                timestamp=datetime.fromisoformat(a['timestamp']),
            )
            if 'selector_chain' in a:
                action.selector_chain = SelectorChain(**a['selector_chain'])
            if 'form_fields' in a:
                action.form_fields = a['form_fields']
            actions.append(action)

        assertions = [
            WaypointAssertion(
                assertion_type=a['assertion_type'],
                target=a['target'],
                expected=a.get('expected'),
                timestamp=datetime.fromisoformat(a['timestamp']),
            )
            for a in data.get('assertions', [])
        ]

        waypoint = cls(
            url=data['url'],
            actions=actions,
            assertions=assertions,
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            parent_hash=data.get('parent_hash'),
            chain_version=data.get('chain_version', 1),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
        )
        waypoint.update_hash()
        return waypoint

    def verify_hash(self, expected_hash: str) -> bool:
        """
        Verify waypoint integrity by comparing computed hash.

        Args:
            expected_hash: Hash to compare against.

        Returns:
            True if hashes match, False otherwise.
        """
        return self.compute_hash() == expected_hash

    def add_action(
        self,
        action_type: ActionType,
        selector: Optional[str] = None,
        value: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        """
        Add an action to the waypoint.

        Args:
            action_type: Type of action.
            selector: Element selector (optional).
            value: Action value (optional).
            timeout: Action timeout in seconds.
        """
        action = WaypointAction(
            action_type=action_type,
            selector=selector,
            value=value,
            timeout=timeout,
        )
        self.actions.append(action)

    def add_action_with_chain(
        self,
        action_type: ActionType,
        chain: SelectorChain,
        value: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        """
        Add an action with a multi-candidate selector chain.

        Sets both selector (from chain.primary_selector()) for legacy
        compatibility and selector_chain for new verification.

        Args:
            action_type: Type of action.
            chain: SelectorChain with ordered candidates.
            value: Action value (optional).
            timeout: Action timeout in seconds.
        """
        action = WaypointAction(
            action_type=action_type,
            selector=chain.primary_selector(),
            selector_chain=chain,
            value=value,
            timeout=timeout,
        )
        self.actions.append(action)

    def add_assertion(
        self,
        assertion_type: AssertionType,
        target: str,
        expected: Optional[str] = None,
    ) -> None:
        """
        Add an assertion to the waypoint.

        Args:
            assertion_type: Type of assertion.
            target: Assertion target (text, selector, URL, etc.).
            expected: Expected value (optional).
        """
        assertion = WaypointAssertion(
            assertion_type=assertion_type,
            target=target,
            expected=expected,
        )
        self.assertions.append(assertion)
