"""Bridge to svarog-brain for semantic waypoint indexing.

Integrates Nexus waypoints with the house vector store for searchable
navigation guides.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

SVAROG_BRAIN_PATH = os.environ.get('NEXUS_SVAROG_BRAIN_PATH', str(Path.home() / 'svarog-brain'))
if SVAROG_BRAIN_PATH not in sys.path:
    sys.path.insert(0, SVAROG_BRAIN_PATH)

try:
    import brain
    BRAIN_AVAILABLE = True
except ImportError:
    brain = None
    BRAIN_AVAILABLE = False


def summarize_waypoint(waypoint: 'Waypoint') -> str:
    """Generate a searchable text summary of a waypoint.

    Args:
        waypoint: Waypoint to summarize.

    Returns:
        Text suitable for semantic search indexing.
    """
    parts = [
        f"Website: {waypoint.url}",
        f"Description: {waypoint.description}" if waypoint.description else "",
    ]

    if waypoint.actions:
        action_summaries = []
        for action in waypoint.actions[:5]:
            if action.value:
                action_summaries.append(f"{action.action_type}: {action.value}")
            else:
                action_summaries.append(f"{action.action_type}")
        parts.append(f"Actions: {'; '.join(action_summaries)}")

    return " | ".join(p for p in parts if p)


def index_waypoint(waypoint: 'Waypoint') -> Dict[str, Any]:
    """Index a waypoint in svarog-brain.

    Args:
        waypoint: Waypoint to index.

    Returns:
        Result dict with 'added' and 'skipped' counts.

    Raises:
        RuntimeError: If svarog-brain is not available.
    """
    if not BRAIN_AVAILABLE:
        raise RuntimeError(
            f'svarog-brain not found at {SVAROG_BRAIN_PATH}; '
            'set NEXUS_SVAROG_BRAIN_PATH to override'
        )

    text = summarize_waypoint(waypoint)
    meta = {
        'kind': 'nexus_waypoint',
        'url': waypoint.url,
        'waypoint_hash': waypoint.hash,
        'ipfs_hash': waypoint.ipfs_hash or '',
        'chain_version': waypoint.chain_version,
    }

    try:
        added, skipped = brain.add([{**meta, 'text': text, 'source': waypoint.hash}])
        return {'added': added, 'skipped': skipped}
    except Exception as e:
        raise RuntimeError(f'Failed to index waypoint: {e}')


def search_waypoints(query: str, k: int = 8) -> List[Dict[str, Any]]:
    """Search indexed waypoints by semantic similarity.

    Args:
        query: Search query (natural language or keywords).
        k: Number of results to return.

    Returns:
        List of matching waypoint metadata dicts.

    Raises:
        RuntimeError: If svarog-brain is not available.
    """
    if not BRAIN_AVAILABLE:
        raise RuntimeError(
            f'svarog-brain not found at {SVAROG_BRAIN_PATH}; '
            'set NEXUS_SVAROG_BRAIN_PATH to override'
        )

    try:
        results = brain.search(query, k=k, where={'kind': 'nexus_waypoint'})
        return results
    except Exception as e:
        raise RuntimeError(f'Failed to search waypoints: {e}')
