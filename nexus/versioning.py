"""Version chain management for waypoints.

Tracks parent-child relationships between waypoint versions, enabling
historical queries and version diffing.
"""

from typing import List, Optional

from nexus.waypoint import Waypoint, WaypointAction
from nexus.store import db_session


class WaypointVersionChain:
    """Manages version chains for waypoints."""

    @staticmethod
    def create_next_version(previous: Waypoint,
                           updated_actions: List[WaypointAction],
                           reason: str = '') -> Waypoint:
        """Create a new version of a waypoint from a previous version.

        Args:
            previous: The previous waypoint to base this version on.
            updated_actions: New list of actions for this version.
            reason: Human-readable reason for the new version.

        Returns:
            A new Waypoint with parent_hash set and chain_version incremented.
        """
        previous.update_hash()
        new_wp = Waypoint(
            url=previous.url,
            actions=updated_actions,
            assertions=previous.assertions,
            description=previous.description,
            version=previous.version,
            parent_hash=previous.hash,
            chain_version=previous.chain_version + 1,
        )
        new_wp.update_hash()
        return new_wp

    @staticmethod
    def record_version(waypoint: Waypoint,
                      ipfs_hash: Optional[str] = None) -> None:
        """Record a waypoint in the version chain database.

        Args:
            waypoint: Waypoint to record.
            ipfs_hash: Optional IPFS hash if this waypoint was pinned.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO waypoint_versions
                (local_hash, ipfs_hash, parent_hash, chain_version, url, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (waypoint.hash, ipfs_hash, waypoint.parent_hash,
                  waypoint.chain_version, waypoint.url,
                  waypoint.created_at.isoformat()))

    @staticmethod
    def walk_chain(local_hash: str) -> List[dict]:
        """Walk the version chain backwards from a given waypoint hash.

        Args:
            local_hash: Starting waypoint hash.

        Returns:
            List of version records in parent -> child order.
        """
        chain = []
        current = local_hash

        with db_session() as conn:
            cursor = conn.cursor()
            while current:
                cursor.execute("""
                    SELECT local_hash, ipfs_hash, parent_hash, chain_version, url, created_at
                    FROM waypoint_versions WHERE local_hash = ?
                """, (current,))
                row = cursor.fetchone()
                if not row:
                    break

                chain.append({
                    'local_hash': row[0],
                    'ipfs_hash': row[1],
                    'parent_hash': row[2],
                    'chain_version': row[3],
                    'url': row[4],
                    'created_at': row[5],
                })
                current = row[2]  # parent_hash

        return list(reversed(chain))
