"""Multi-candidate selector strategies for resilient element lookup.

Replaces single brittle selector strings with ordered chains of fallback
strategies (CSS, XPath, ARIA role, text matching). Each candidate tracks
success/fail history and confidence, decoded from live Playwright execution.
"""

import re
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SelectorStrategy(str, Enum):
    """Strategy for locating an element on a page."""
    CSS = "css"
    XPATH = "xpath"
    ARIA_ROLE = "aria_role"
    TEXT_EXACT = "text_exact"
    TEXT_REGEX = "text_regex"


class SelectorCandidate(BaseModel):
    """A single selector strategy + value with confidence tracking.

    Confidence is a float in [0, 1] computed from verification history:
    success rate * exponential time decay * structural drift penalty.
    """
    strategy: SelectorStrategy
    value: str
    role: Optional[str] = None
    flags: int = 0
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    verified_count: int = 0
    failed_count: int = 0

    class Config:
        use_enum_values = False


class SelectorChain(BaseModel):
    """Ordered list of selector candidates, tried in confidence order.

    Provides a graceful degradation path: if the primary (CSS/XPath) selector
    fails due to site redesign, try text matching, then ARIA. Every attempt
    is recorded in the verification graph.
    """
    candidates: List[SelectorCandidate] = Field(default_factory=list)

    def ordered(self) -> List[SelectorCandidate]:
        """Return candidates sorted by confidence (descending)."""
        return sorted(self.candidates, key=lambda c: c.confidence, reverse=True)

    def primary_selector(self) -> Optional[str]:
        """Return the best CSS or XPath selector, if any."""
        for c in self.ordered():
            if c.strategy in (SelectorStrategy.CSS, SelectorStrategy.XPATH):
                return c.value
        return None

    def add_candidate(self, strategy: SelectorStrategy, value: str,
                      confidence: float = 0.5, role: Optional[str] = None,
                      flags: int = 0) -> None:
        """Add a candidate to the chain."""
        self.candidates.append(
            SelectorCandidate(
                strategy=strategy, value=value, role=role, flags=flags,
                confidence=confidence
            )
        )

    def best(self) -> Optional[SelectorCandidate]:
        """Return the highest-confidence candidate."""
        candidates = self.ordered()
        return candidates[0] if candidates else None


def resolve_candidate_playwright(page, candidate: SelectorCandidate):
    """Resolve a SelectorCandidate to a Playwright Locator.

    Dispatch to the appropriate Playwright locator method based on strategy.
    """
    if candidate.strategy == SelectorStrategy.CSS:
        return page.locator(candidate.value)
    elif candidate.strategy == SelectorStrategy.XPATH:
        return page.locator(f"xpath={candidate.value}")
    elif candidate.strategy == SelectorStrategy.ARIA_ROLE:
        return page.get_by_role(candidate.role, name=candidate.value)
    elif candidate.strategy == SelectorStrategy.TEXT_EXACT:
        return page.get_by_text(candidate.value, exact=True)
    elif candidate.strategy == SelectorStrategy.TEXT_REGEX:
        pattern = re.compile(candidate.value, candidate.flags)
        return page.get_by_text(pattern)
    else:
        raise ValueError(f"Unknown selector strategy: {candidate.strategy}")
