"""Verification graph: ground-truth tracking of selector claims via live Playwright execution.

Every selector (CSS/XPath/ARIA/text) is a claim until proven against a live page.
Verigraph records each verification event: timestamp, DOM fingerprint, success/fail.
Confidence is computed from success rate, time decay, and structural drift.

This ensures selectors are ONLY trusted because Playwright proved them — never
because an LLM guessed they looked right.
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nexus.selectors import SelectorCandidate, SelectorStrategy
from nexus.store import db_session


def compute_claim_id(waypoint_id: str, action_index: int,
                     strategy: SelectorStrategy, value: str) -> str:
    """Deterministic claim ID from waypoint+action+strategy+value."""
    s = f"{waypoint_id}#{action_index}#{strategy}#{value}"
    return hashlib.sha256(s.encode()).hexdigest()[:16]


async def compute_dom_fingerprint(page) -> str:
    """Compute a structural hash of the DOM.

    Sensitive to layout/tag structure, insensitive to text/content changes.
    Used to detect when a site redesign invalidates a selector.
    """
    try:
        elements = await page.evaluate("""
            () => {
                const tags = new Set();
                document.body.querySelectorAll('*').forEach(el => {
                    tags.add(el.tagName + (el.id ? '#' + el.id : '') +
                             (el.className ? '.' + el.className.split(' ')[0] : ''));
                });
                return JSON.stringify(Array.from(tags).sort());
            }
        """)
        return hashlib.sha256(elements.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"


class Verigraph:
    """Append-only verification graph for selector claims."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def record_claim(self, waypoint_id: str, action_index: int,
                     candidate: SelectorCandidate) -> str:
        """Record a new claim (selector candidate) in the database."""
        claim_id = compute_claim_id(waypoint_id, action_index,
                                    candidate.strategy, candidate.value)
        with db_session(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO claims
                (claim_id, waypoint_id, action_index, strategy, value, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (claim_id, waypoint_id, action_index, candidate.strategy.value,
                  candidate.value, candidate.role, datetime.utcnow().isoformat()))
        return claim_id

    def record_verification(self, claim_id: str, dom_fingerprint: str,
                            success: bool, latency_ms: float,
                            evidence_type: str = "action",
                            error: Optional[str] = None) -> None:
        """Record a verification event for a claim."""
        event_id = str(uuid.uuid4())
        with db_session(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO verifications
                (event_id, claim_id, timestamp, dom_fingerprint, success,
                 evidence_type, latency_ms, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, claim_id, datetime.utcnow().isoformat(),
                  dom_fingerprint, int(success), evidence_type, latency_ms, error))

    def confidence_for(self, claim_id: str,
                      now: Optional[datetime] = None,
                      half_life_days: float = 30.0) -> float:
        """Compute confidence score from verification history.

        Formula: success_rate * time_decay * drift_penalty
        - success_rate: Laplace-smoothed (successes+1)/(total+2)
        - time_decay: exponential with half_life_days
        - drift_penalty: 0.5 if DOM structure changed, else 1.0
        """
        if now is None:
            now = datetime.utcnow()

        with db_session(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT success, timestamp, dom_fingerprint
                FROM verifications WHERE claim_id = ?
                ORDER BY timestamp DESC LIMIT 100
            """, (claim_id,))
            rows = cursor.fetchall()

        if not rows:
            return 0.5

        successes = sum(1 for r in rows if r[0])
        failures = len(rows) - successes
        success_rate = (successes + 1) / (len(rows) + 2)

        latest_timestamp = datetime.fromisoformat(rows[0][1])
        days_ago = (now - latest_timestamp).total_seconds() / 86400
        time_decay = 0.5 ** (days_ago / half_life_days)

        latest_fp = rows[0][2]
        last_success_fp = next(
            (r[2] for r in rows if r[0]),
            None
        )
        drift_penalty = 0.5 if (last_success_fp and
                                last_success_fp != latest_fp) else 1.0

        return min(1.0, success_rate * time_decay * drift_penalty)

    def is_stale(self, claim_id: str, max_age_days: int = 14,
                 min_confidence: float = 0.3) -> bool:
        """Check if a claim needs reverification."""
        confidence = self.confidence_for(claim_id)
        if confidence < min_confidence:
            return True

        with db_session(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(timestamp) FROM verifications WHERE claim_id = ?
            """, (claim_id,))
            row = cursor.fetchone()

        if not row or not row[0]:
            return True

        last_verified = datetime.fromisoformat(row[0])
        age_days = (datetime.utcnow() - last_verified).total_seconds() / 86400
        return age_days > max_age_days

    def best_candidates(self, waypoint_id: str, action_index: int,
                        k: int = 5) -> List[Tuple[str, float]]:
        """Return top-k candidates for an action by confidence."""
        with db_session(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT claim_id FROM claims
                WHERE waypoint_id = ? AND action_index = ?
                ORDER BY created_at DESC LIMIT ?
            """, (waypoint_id, action_index, k))
            claim_ids = [row[0] for row in cursor.fetchall()]

        return [
            (cid, self.confidence_for(cid))
            for cid in claim_ids
        ]
