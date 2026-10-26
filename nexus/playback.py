"""
Playback engine for replaying recorded waypoints.

Executes recorded navigation sequences with assertion verification.
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from nexus.waypoint import Waypoint, ActionType, AssertionType
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
    Replays recorded waypoints using Playwright.

    Attributes:
        browser: Playwright browser instance.
        context: Playwright browser context.
        page: Currently active page.
        waypoint: Waypoint being replayed.
        strict_assertions: Whether to fail on assertion errors.
    """

    def __init__(self, strict_assertions: bool = True) -> None:
        """
        Initialize playback engine.

        Args:
            strict_assertions: If True, fail on any assertion error.
                              If False, log warnings and continue.
        """
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.waypoint: Optional[Waypoint] = None
        self.strict_assertions = strict_assertions

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

                # Navigate to initial URL
                logger.info(f'Replaying waypoint from {waypoint.url}')
                await self.page.goto(waypoint.url, wait_until='networkidle')

                # Execute actions
                for action in waypoint.actions:
                    await self._execute_action(action)

                # Verify assertions
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

    async def _execute_action(self, action) -> None:
        """
        Execute a single action.

        Args:
            action: WaypointAction to execute.

        Raises:
            PlaybackError: If action execution fails.
        """
        if not self.page:
            raise PlaybackError('Page not initialized')

        try:
            if action.action_type == ActionType.CLICK:
                if not action.selector:
                    raise PlaybackError('Click action missing selector')

                await self.page.click(action.selector, timeout=action.timeout * 1000)
                logger.debug(f'Clicked: {action.selector}')

            elif action.action_type == ActionType.DOUBLE_CLICK:
                if not action.selector:
                    raise PlaybackError('Double click action missing selector')

                await self.page.dblclick(action.selector, timeout=action.timeout * 1000)
                logger.debug(f'Double clicked: {action.selector}')

            elif action.action_type == ActionType.TYPE:
                if not action.selector or not action.value:
                    raise PlaybackError('Type action missing selector or value')

                await self.page.fill(action.selector, action.value, timeout=action.timeout * 1000)
                logger.debug(f'Typed: {action.selector} = {action.value}')

            elif action.action_type == ActionType.SELECT:
                if not action.selector or not action.value:
                    raise PlaybackError('Select action missing selector or value')

                await self.page.select_option(
                    action.selector,
                    action.value,
                    timeout=action.timeout * 1000,
                )
                logger.debug(f'Selected: {action.selector} = {action.value}')

            elif action.action_type == ActionType.HOVER:
                if not action.selector:
                    raise PlaybackError('Hover action missing selector')

                await self.page.hover(action.selector, timeout=action.timeout * 1000)
                logger.debug(f'Hovered: {action.selector}')

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

            elif action.action_type == ActionType.NAVIGATE:
                if not action.value:
                    raise PlaybackError('Navigate action missing value')

                await self.page.goto(action.value, wait_until='networkidle')
                logger.debug(f'Navigated: {action.value}')

            elif action.action_type == ActionType.WAIT:
                await asyncio.sleep(action.timeout)
                logger.debug(f'Waited: {action.timeout}s')

            elif action.action_type == ActionType.SCREENSHOT:
                if not action.value:
                    raise PlaybackError('Screenshot action missing filename')

                await self.page.screenshot(path=action.value)
                logger.debug(f'Screenshot saved: {action.value}')

            else:
                raise PlaybackError(f'Unknown action type: {action.action_type}')

        except Exception as e:
            raise PlaybackError(f'Failed to execute action {action.action_type}: {e}')

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
