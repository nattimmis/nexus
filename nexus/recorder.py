"""
Playwright-based navigation recorder for Nexus.

Records user interactions (clicks, typing, navigation) as waypoints
that can be replayed or stored on IPFS.
"""

import asyncio
from typing import Optional, List, Callable
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from nexus.waypoint import Waypoint, ActionType, AssertionType
from nexus.logging_util import get_logger

logger = get_logger(__name__)


class NavigationRecorder:
    """
    Records web navigation sequences using Playwright.

    Attributes:
        browser: Playwright browser instance.
        context: Playwright browser context.
        page: Currently active page.
        waypoint: Current waypoint being recorded.
        recording: Whether recording is active.
    """

    def __init__(self) -> None:
        """Initialize navigation recorder."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.waypoint: Optional[Waypoint] = None
        self.recording = False
        self._action_handlers: List[Callable] = []

    async def start_recording(self, url: str, headless: bool = False) -> None:
        """
        Start recording navigation on a webpage.

        Args:
            url: Initial URL to navigate to.
            headless: Whether to run browser in headless mode.

        Raises:
            RuntimeError: If browser fails to launch or page load times out.
        """
        try:
            async with async_playwright() as p:
                self.browser = await p.chromium.launch(headless=headless)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

                # Initialize waypoint
                self.waypoint = Waypoint(url=url)

                # Register event listeners
                await self._register_listeners()

                # Navigate to initial URL
                logger.info(f'Navigating to {url}')
                await self.page.goto(url, wait_until='networkidle')
                self.recording = True

                # Wait for user to complete recording
                await self._wait_for_completion()

        except Exception as e:
            logger.error(f'Recording error: {e}')
            raise
        finally:
            await self.stop_recording()

    async def stop_recording(self) -> Waypoint:
        """
        Stop recording and clean up browser resources.

        Returns:
            Recorded waypoint.
        """
        if self.browser:
            await self.browser.close()

        self.recording = False
        logger.info('Recording stopped')

        if not self.waypoint:
            self.waypoint = Waypoint(url='')

        self.waypoint.update_hash()
        return self.waypoint

    async def _register_listeners(self) -> None:
        """Register event listeners on page for interaction tracking."""
        if not self.page:
            return

        # Track clicks
        self.page.on(
            'framenavigated',
            lambda frame: asyncio.create_task(self._on_navigation(frame.page)),
        )

    async def _on_navigation(self, page: Page) -> None:
        """
        Handle page navigation events.

        Args:
            page: The page that navigated.
        """
        if not self.recording or not self.waypoint:
            return

        url = page.url
        logger.info(f'Navigation recorded: {url}')

        # Add navigation action
        self.waypoint.add_action(
            ActionType.NAVIGATE,
            value=url,
        )

    async def record_click(self, selector: str) -> None:
        """
        Record a click action.

        Args:
            selector: CSS selector of clicked element.

        Raises:
            ValueError: If waypoint not initialized.
        """
        if not self.waypoint:
            raise ValueError('Recording not started')

        self.waypoint.add_action(ActionType.CLICK, selector=selector)
        logger.debug(f'Click recorded: {selector}')

    async def record_type(self, selector: str, text: str) -> None:
        """
        Record a text input action.

        Args:
            selector: CSS selector of input element.
            text: Text to type.

        Raises:
            ValueError: If waypoint not initialized.
        """
        if not self.waypoint:
            raise ValueError('Recording not started')

        self.waypoint.add_action(ActionType.TYPE, selector=selector, value=text)
        logger.debug(f'Type recorded: {selector} = {text}')

    async def record_select(self, selector: str, value: str) -> None:
        """
        Record a select/dropdown action.

        Args:
            selector: CSS selector of select element.
            value: Selected value.

        Raises:
            ValueError: If waypoint not initialized.
        """
        if not self.waypoint:
            raise ValueError('Recording not started')

        self.waypoint.add_action(ActionType.SELECT, selector=selector, value=value)
        logger.debug(f'Select recorded: {selector} = {value}')

    async def record_wait(self, timeout: float = 5.0) -> None:
        """
        Record a wait action.

        Args:
            timeout: Timeout in seconds.

        Raises:
            ValueError: If waypoint not initialized.
        """
        if not self.waypoint:
            raise ValueError('Recording not started')

        self.waypoint.add_action(ActionType.WAIT, timeout=timeout)
        logger.debug(f'Wait recorded: {timeout}s')

    async def record_assertion_text_present(self, text: str) -> None:
        """
        Record an assertion that text is present on page.

        Args:
            text: Text to assert.

        Raises:
            ValueError: If waypoint not initialized.
        """
        if not self.waypoint:
            raise ValueError('Recording not started')

        self.waypoint.add_assertion(AssertionType.TEXT_PRESENT, target=text)
        logger.debug(f'Assertion recorded: text present = {text}')

    async def record_assertion_element_visible(self, selector: str) -> None:
        """
        Record an assertion that element is visible.

        Args:
            selector: CSS selector of element.

        Raises:
            ValueError: If waypoint not initialized.
        """
        if not self.waypoint:
            raise ValueError('Recording not started')

        self.waypoint.add_assertion(AssertionType.ELEMENT_VISIBLE, target=selector)
        logger.debug(f'Assertion recorded: element visible = {selector}')

    async def record_assertion_url_matches(self, pattern: str) -> None:
        """
        Record an assertion that URL matches pattern.

        Args:
            pattern: URL pattern or regex.

        Raises:
            ValueError: If waypoint not initialized.
        """
        if not self.waypoint:
            raise ValueError('Recording not started')

        self.waypoint.add_assertion(AssertionType.URL_MATCHES, target=pattern)
        logger.debug(f'Assertion recorded: url matches = {pattern}')

    async def _wait_for_completion(self) -> None:
        """
        Wait for user to indicate recording is complete.
        In interactive mode, this waits for user input.
        """
        try:
            # Simple timeout-based completion for automation
            await asyncio.sleep(300)  # 5-minute timeout
        except KeyboardInterrupt:
            logger.info('Recording interrupted by user')


class InteractiveRecorder(NavigationRecorder):
    """
    Interactive recorder with manual step-by-step recording.

    Allows pausing, adding assertions, and validating actions interactively.
    """

    async def manual_step(self) -> None:
        """
        Execute a manual recording step (user action via CLI prompts).

        This is called interactively by CLI to record specific actions.
        """
        pass  # Implemented in CLI integration
