"""Playback engine for replaying recorded waypoints with verification.

Executes recorded navigation sequences with optional Verigraph tracking
for selector confidence and self-healing retry logic.
"""

import asyncio
import hashlib
import time
from typing import Optional, List

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from nexus.waypoint import Waypoint, ActionType, WaypointAction, AssertionType
from nexus.selectors import SelectorCandidate, SelectorChain, SelectorStrategy, resolve_candidate_playwright
from nexus.logging_util import get_logger

logger = get_logger(__name__)


class PlaybackError(Exception):
    """Base exception for playback errors."""
    pass


class AssertionFailedError(PlaybackError):
    """Raised when an assertion fails during playback."""
    pass


class ElementNotFoundError(PlaybackError):
    """Raised when an element is not found during playback."""
    pass


class NavigationPlayback:
    """
    Replays recorded waypoints using Playwright with optional verification.

    Attributes:
        browser: Playwright browser instance.
        context: Playwright browser context.
        page: Currently active page.
        waypoint: Waypoint being replayed.
        strict_assertions: Whether to fail on assertion errors.
        verigraph: Optional verification graph for tracking selector confidence.
    """

    def __init__(self, strict_assertions: bool = True,
                 verigraph: Optional['Verigraph'] = None) -> None:
        """
        Initialize playback engine.

        Args:
            strict_assertions: If True, fail on any assertion error.
            verigraph: Optional Verigraph instance for recording verification events.
        """
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.waypoint: Optional[Waypoint] = None
        self.strict_assertions = strict_assertions
        self.verigraph = verigraph

    async def replay_waypoint(
        self,
        waypoint: Waypoint,
        headless: bool = True,
    ) -> bool:
        """
        Replay a recorded waypoint.

        Args:
            waypoint: Waypoint to replay.
            headless: Whether to run browser in headless mode.

        Returns:
            True if replay completed successfully.

        Raises:
            PlaybackError: If replay fails.
        """
        try:
            async with async_playwright() as p:
                self.browser = await p.chromium.launch(headless=headless)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
                self.waypoint = waypoint

                logger.info(f'Replaying waypoint from {waypoint.url}')
                await self.page.goto(waypoint.url, wait_until='networkidle')

                for action_idx, action in enumerate(waypoint.actions):
                    await self._execute_action(action, action_idx)

                for assertion in waypoint.assertions:
                    await self._verify_assertion(assertion)

                logger.info('Waypoint replay completed successfully')
                return True

        except PlaybackError as e:
            logger.error(f'Playback error: {e}')
            if self.strict_assertions:
                raise
            return False
        except Exception as e:
            logger.error(f'Unexpected playback error: {e}')
            raise
        finally:
            if self.browser:
                await self.browser.close()

    async def _execute_action(self, action: WaypointAction,
                             action_index: int = -1) -> None:
        """
        Execute a single action with optional multi-candidate fallback.

        If selector_chain is set, tries candidates in confidence order.
        If selector_chain is not set, falls back to single selector (legacy mode).

        Args:
            action: WaypointAction to execute.
            action_index: Index in waypoint.actions (for verigraph tracking).

        Raises:
            PlaybackError: If action execution fails.
            ElementNotFoundError: If all selector candidates fail.
        """
        if not self.page:
            raise PlaybackError('Page not initialized')

        if action.action_type in (ActionType.NAVIGATE, ActionType.WAIT,
                                   ActionType.SCROLL, ActionType.SCREENSHOT):
            await self._execute_non_selector_action(action)
            return

        candidates = self._candidates_for(action)
        last_error = None

        for candidate in candidates:
            start = time.monotonic()
            try:
                locator = resolve_candidate_playwright(self.page, candidate)
                await self._dispatch_action(action, locator)

                if self.verigraph and action_index >= 0:
                    fp = await compute_dom_fingerprint(self.page)
                    claim_id = self._claim_id(action_index, candidate)
                    self.verigraph.record_verification(
                        claim_id, fp, True,
                        (time.monotonic() - start) * 1000,
                        evidence_type='action'
                    )
                return

            except Exception as e:
                last_error = e
                if self.verigraph and action_index >= 0:
                    try:
                        fp = await compute_dom_fingerprint(self.page)
                    except Exception:
                        fp = "unknown"
                    claim_id = self._claim_id(action_index, candidate)
                    self.verigraph.record_verification(
                        claim_id, fp, False,
                        (time.monotonic() - start) * 1000,
                        evidence_type='action',
                        error=str(e)
                    )
                logger.warning(f'Candidate failed ({candidate.strategy}={candidate.value}): {e}')

        if len(candidates) > 1:
            raise ElementNotFoundError(
                f'All {len(candidates)} selector candidates failed: {last_error}'
            )
        raise PlaybackError(f'Failed to execute action {action.action_type}: {last_error}')

    async def _execute_non_selector_action(self, action: WaypointAction) -> None:
        """Execute actions that don't require selectors (navigate, wait, scroll, etc)."""
        try:
            if action.action_type == ActionType.NAVIGATE:
                if not action.value:
                    raise PlaybackError('Navigate action missing value')
                await self.page.goto(action.value, wait_until='networkidle')
                logger.debug(f'Navigated: {action.value}')

            elif action.action_type == ActionType.WAIT:
                await asyncio.sleep(action.timeout)
                logger.debug(f'Waited: {action.timeout}s')

            elif action.action_type == ActionType.SCROLL:
                if not action.value:
                    raise PlaybackError('Scroll action missing value')
                direction = action.value.lower()
                if direction == 'down':
                    await self.page.evaluate('window.scrollBy(0, window.innerHeight)')
                elif direction == 'up':
                    await self.page.evaluate('window.scrollBy(0, -window.innerHeight)')
                else:
                    raise PlaybackError(f'Invalid scroll direction: {direction}')
                logger.debug(f'Scrolled: {direction}')

            elif action.action_type == ActionType.SCREENSHOT:
                if not action.value:
                    raise PlaybackError('Screenshot action missing filename')
                await self.page.screenshot(path=action.value)
                logger.debug(f'Screenshot saved: {action.value}')

        except Exception as e:
            raise PlaybackError(f'Failed to execute {action.action_type}: {e}')

    async def _dispatch_action(self, action: WaypointAction, locator) -> None:
        """Dispatch action execution to the appropriate Playwright method."""
        if action.action_type == ActionType.CLICK:
            await locator.click(timeout=action.timeout * 1000)
            logger.debug(f'Clicked')

        elif action.action_type == ActionType.DOUBLE_CLICK:
            await locator.dblclick(timeout=action.timeout * 1000)
            logger.debug(f'Double clicked')

        elif action.action_type == ActionType.TYPE:
            if not action.value:
                raise PlaybackError('Type action missing value')
            await locator.fill(action.value, timeout=action.timeout * 1000)
            logger.debug(f'Typed: {action.value}')

        elif action.action_type == ActionType.SELECT:
            if not action.value:
                raise PlaybackError('Select action missing value')
            await locator.select_option(action.value, timeout=action.timeout * 1000)
            logger.debug(f'Selected: {action.value}')

        elif action.action_type == ActionType.HOVER:
            await locator.hover(timeout=action.timeout * 1000)
            logger.debug(f'Hovered')

        elif action.action_type == ActionType.FILL_FORM:
            if not action.form_fields:
                raise PlaybackError('Fill form action missing form_fields')
            for selector, text in action.form_fields.items():
                await self.page.fill(selector, text, timeout=action.timeout * 1000)
            logger.debug(f'Filled form: {len(action.form_fields)} fields')

        else:
            raise PlaybackError(f'Unknown action type: {action.action_type}')

    def _candidates_for(self, action: WaypointAction) -> List[SelectorCandidate]:
        """Get ordered list of selector candidates for an action.

        If selector_chain is present, return its ordered candidates.
        Otherwise, synthesize a single-candidate list from legacy selector field.
        """
        if action.selector_chain and action.selector_chain.candidates:
            return action.selector_chain.ordered()

        if action.selector:
            return [SelectorCandidate(
                strategy=SelectorStrategy.CSS,
                value=action.selector,
                confidence=1.0
            )]

        raise PlaybackError(f'Action {action.action_type} has no selector or selector_chain')

    def _claim_id(self, action_index: int, candidate: SelectorCandidate) -> str:
        """Generate a claim ID for verigraph tracking."""
        if not self.waypoint:
            return "unknown"
        s = f"{self.waypoint.hash}#{action_index}#{candidate.strategy}#{candidate.value}"
        return hashlib.sha256(s.encode()).hexdigest()[:16]

    async def _verify_assertion(self, assertion) -> None:
        """
        Verify a single assertion.

        Args:
            assertion: WaypointAssertion to verify.

        Raises:
            AssertionFailedError: If assertion verification fails (in strict mode).
        """
        if not self.page:
            raise PlaybackError('Page not initialized')

        try:
            if assertion.assertion_type == AssertionType.TEXT_PRESENT:
                is_present = await self.page.locator(f'text={assertion.target}').is_visible()
                if not is_present:
                    raise AssertionFailedError(
                        f'Text not found on page: {assertion.target}'
                    )
                logger.debug(f'Assertion passed: text present = {assertion.target}')

            elif assertion.assertion_type == AssertionType.ELEMENT_VISIBLE:
                is_visible = await self.page.locator(assertion.target).is_visible()
                if not is_visible:
                    raise AssertionFailedError(
                        f'Element not visible: {assertion.target}'
                    )
                logger.debug(f'Assertion passed: element visible = {assertion.target}')

            elif assertion.assertion_type == AssertionType.ELEMENT_HIDDEN:
                is_hidden = await self.page.locator(assertion.target).is_hidden()
                if not is_hidden:
                    raise AssertionFailedError(
                        f'Element not hidden: {assertion.target}'
                    )
                logger.debug(f'Assertion passed: element hidden = {assertion.target}')

            elif assertion.assertion_type == AssertionType.URL_MATCHES:
                current_url = self.page.url
                if assertion.target not in current_url:
                    raise AssertionFailedError(
                        f'URL does not match. Expected: {assertion.target}, '
                        f'Got: {current_url}'
                    )
                logger.debug(f'Assertion passed: url matches = {assertion.target}')

            elif assertion.assertion_type == AssertionType.TITLE_CONTAINS:
                title = await self.page.title()
                if assertion.target not in title:
                    raise AssertionFailedError(
                        f'Title does not contain. Expected: {assertion.target}, '
                        f'Got: {title}'
                    )
                logger.debug(f'Assertion passed: title contains = {assertion.target}')

            elif assertion.assertion_type == AssertionType.VALUE_EQUALS:
                if not assertion.target or not assertion.expected:
                    raise AssertionFailedError('Value assertion missing target or expected')

                element_value = await self.page.locator(assertion.target).input_value()
                if element_value != assertion.expected:
                    raise AssertionFailedError(
                        f'Value does not match. Expected: {assertion.expected}, '
                        f'Got: {element_value}'
                    )
                logger.debug(
                    f'Assertion passed: value equals = {assertion.target} '
                    f'== {assertion.expected}'
                )

            else:
                raise AssertionFailedError(
                    f'Unknown assertion type: {assertion.assertion_type}'
                )

        except AssertionFailedError:
            logger.warning(f'Assertion failed: {assertion.assertion_type}')
            if self.strict_assertions:
                raise
        except Exception as e:
            error_msg = f'Error verifying assertion: {e}'
            logger.error(error_msg)
            if self.strict_assertions:
                raise AssertionFailedError(error_msg)


async def compute_dom_fingerprint(page: Page) -> str:
    """Compute structural DOM hash for drift detection."""
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
        import hashlib
        return hashlib.sha256(elements.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"
