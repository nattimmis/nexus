"""Non-destructive browser crawler for discovering interactive elements.

Crawls allowed sites, probes elements for visibility/existence, and
records candidates for later manual or automatic waypoint creation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from nexus.logging_util import get_logger
from nexus.selectors import SelectorCandidate, SelectorStrategy

logger = get_logger(__name__)


@dataclass
class SiteConfig:
    """Configuration for a site to crawl."""
    name: str
    base_url: str
    allow_paths: List[str] = field(default_factory=list)
    excluded_paths: List[str] = field(default_factory=list)
    max_depth: int = 2
    max_pages: int = 25
    skip_submit_buttons: bool = True


class NonDestructiveCrawler:
    """Browser crawler that only probes elements, never modifies state."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def crawl_site(self, site: SiteConfig) -> List[dict]:
        """Crawl a site within configured bounds.

        Args:
            site: SiteConfig with domain and path constraints.

        Returns:
            List of discovered interactive element candidates.
        """
        candidates = []
        visited: Set[str] = set()

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                self.browser = await p.chromium.launch(headless=self.headless)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()

                queue = [site.base_url]
                depth = {site.base_url: 0}

                while queue and len(visited) < site.max_pages:
                    url = queue.pop(0)
                    if url in visited:
                        continue

                    if not self._is_allowed_path(url, site):
                        continue

                    if depth.get(url, 0) >= site.max_depth:
                        continue

                    visited.add(url)
                    logger.info(f'Crawling: {url}')

                    try:
                        await self.page.goto(url, wait_until='networkidle', timeout=10000)
                        found = await self._probe_page(self.page, site)
                        candidates.extend(found)

                        links = await self._extract_links(self.page, site.base_url)
                        for link in links:
                            if link not in visited:
                                queue.append(link)
                                depth[link] = depth.get(url, 0) + 1

                    except Exception as e:
                        logger.warning(f'Failed to crawl {url}: {e}')

        finally:
            if self.browser:
                await self.browser.close()

        return candidates

    async def _probe_page(self, page: Page, site: SiteConfig) -> List[dict]:
        """Probe a page for interactive elements.

        Args:
            page: Playwright page.
            site: Site configuration.

        Returns:
            List of probed element candidates.
        """
        candidates = []

        buttons = await page.query_selector_all('button, a, input[type=submit]')
        for button in buttons:
            if site.skip_submit_buttons:
                btn_type = await button.get_attribute('type')
                if btn_type == 'submit':
                    continue

            try:
                if await button.is_visible():
                    text = await button.inner_text()
                    selector = await page.evaluate(
                        'el => el.matches("button") ? "button" : el.tagName.toLowerCase()',
                        button
                    )
                    candidates.append({
                        'strategy': SelectorStrategy.TEXT_EXACT.value,
                        'value': text or '',
                        'type': 'button',
                        'visible': True,
                    })
            except Exception as e:
                logger.debug(f'Failed to probe button: {e}')

        inputs = await page.query_selector_all('input[type=text], input[type=email], textarea')
        for inp in inputs:
            try:
                if await inp.is_visible():
                    placeholder = await inp.get_attribute('placeholder')
                    candidates.append({
                        'strategy': SelectorStrategy.ARIA_ROLE.value,
                        'value': placeholder or 'textbox',
                        'role': 'textbox',
                        'visible': True,
                    })
            except Exception as e:
                logger.debug(f'Failed to probe input: {e}')

        return candidates

    async def _extract_links(self, page: Page, base_url: str) -> List[str]:
        """Extract links from a page."""
        try:
            links = await page.query_selector_all('a[href]')
            urls = []
            for link in links:
                href = await link.get_attribute('href')
                if href and href.startswith('/'):
                    urls.append(urljoin(base_url, href))
            return urls
        except Exception as e:
            logger.debug(f'Failed to extract links: {e}')
            return []

    def _is_allowed_path(self, url: str, site: SiteConfig) -> bool:
        """Check if URL is within allowed paths."""
        parsed = urlparse(url)
        path = parsed.path or '/'

        if site.excluded_paths:
            for excluded in site.excluded_paths:
                if path.startswith(excluded):
                    return False

        if site.allow_paths:
            for allowed in site.allow_paths:
                if path.startswith(allowed) or allowed == '/':
                    return True
            return False

        return True
