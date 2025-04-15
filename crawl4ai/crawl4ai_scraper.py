import asyncio
import json
import os
from typing import Dict, Any, List, Optional, Tuple, Union
import logging
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('crawl4ai_scraper')


class Crawl4AIScraper:
    """
    Advanced web scraper using Crawl4AI approach and Playwright for browser automation.
    Supports JavaScript rendering, login, session persistence, and stealth mode.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scraper with configuration.

        Args:
            config: Dictionary containing scraping configuration
        """
        self.config = config
        self.base_url = config['url']
        self.headers = config.get('headers', {})
        self.session_name = config.get('session', 'default')
        self.cookies_file = f"cookies_{self.session_name}.json"
        self.browser = None
        self.context = None
        self.page = None
        self.stealth_mode = config.get('stealth_mode', True)

    async def __aenter__(self):
        """Context manager entry for async with support."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit for async with support."""
        await self.close()

    async def initialize(self):
        """Initialize the browser, context and load cookies if available."""
        playwright = await async_playwright().start()

        # Launch browser with appropriate settings
        self.browser = await playwright.chromium.launch(
            headless=not self.config.get('visible', False),
            args=['--disable-blink-features=AutomationControlled']
        )

        # Set up context with various options
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': self.headers.get('User-Agent',
                                           'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
        }

        self.context = await self.browser.new_context(**context_options)

        # Apply stealth mode techniques to avoid detection
        if self.stealth_mode:
            await self._apply_stealth_mode()

        # Load cookies if available
        await self._load_cookies()

        # Create a new page
        self.page = await self.context.new_page()

        # Set extra HTTP headers
        if self.headers:
            await self.page.set_extra_http_headers(self.headers)

    async def _apply_stealth_mode(self):
        """Apply various techniques to make browser automation less detectable."""
        # Evaluate JavaScript to modify navigator properties
        await self.context.add_init_script("""
        // Overwrite the 'webdriver' property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });

        // Overwrite chrome runtime
        window.chrome = {
            runtime: {},
        };

        // Pass notifications test
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Overwrite plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/pdf"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }
            ],
        });

        // Prevent iframe detection
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                return window;
            }
        });
        """)

    async def _load_cookies(self):
        """Load cookies from file if available."""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                logger.info(f"Loaded cookies from {self.cookies_file}")
            except Exception as e:
                logger.error(f"Error loading cookies: {e}")

    async def _save_cookies(self):
        """Save cookies to file for session persistence."""
        cookies = await self.context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"Saved cookies to {self.cookies_file}")

    async def close(self):
        """Close browser and clean up resources."""
        if self.browser:
            await self._save_cookies()
            await self.browser.close()
            logger.info("Browser closed and session saved")

    async def login(self, login_config: Dict[str, Any]) -> bool:
        """
        Perform login using the provided configuration.

        Args:
            login_config: Login configuration with URL and actions

        Returns:
            bool: True if login was successful, False otherwise
        """
        if not login_config or not login_config.get('enabled', False):
            logger.info("Login not enabled, skipping")
            return True

        login_url = login_config['url']
        actions = login_config.get('actions', [])

        logger.info(f"Navigating to login page: {login_url}")

        # Navigate to login page
        try:
            await self.page.goto(login_url, wait_until='networkidle')
        except Exception as e:
            logger.error(f"Failed to load login page: {e}")
            return False

        # Execute login actions
        try:
            for action in actions:
                action_type = action['type']

                # Add random delay between actions to appear more human-like
                await asyncio.sleep(random.uniform(0.5, 2.0))

                if action_type == 'fill':
                    selector = action['selector']
                    value = action['value']
                    await self.page.fill(selector, value)
                    logger.info(f"Filled {selector} with value")

                elif action_type == 'click':
                    selector = action['selector']
                    await self.page.click(selector)
                    logger.info(f"Clicked {selector}")

                elif action_type == 'wait':
                    duration = action.get('duration', 1)
                    await asyncio.sleep(duration)
                    logger.info(f"Waited for {duration} seconds")

            # Wait for navigation to complete after submission
            await self.page.wait_for_load_state('networkidle')

            # Save cookies after successful login
            await self._save_cookies()

            # Verify login success using success_indicator if provided
            success_indicator = login_config.get('success_indicator')
            if success_indicator:
                if await self.page.query_selector(success_indicator):
                    logger.info("Login successful (verified by success indicator)")
                    return True
                else:
                    logger.warning("Login may have failed (success indicator not found)")
                    return False

            # If no success indicator provided, assume login was successful
            logger.info("Login actions completed successfully")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def navigate_to(self, url: str) -> str:
        """
        Navigate to a URL and return the page content.

        Args:
            url: URL to navigate to

        Returns:
            str: HTML content of the page
        """
        try:
            logger.info(f"Navigating to {url}")

            # Random delay to avoid detection
            await asyncio.sleep(random.uniform(1, 3))

            # Navigate to the URL
            response = await self.page.goto(url, wait_until='networkidle')

            if not response:
                logger.error(f"Failed to get response from {url}")
                return ""

            if response.status >= 400:
                logger.error(f"HTTP error {response.status} when accessing {url}")
                return ""

            # Wait for the page to be fully loaded
            await self._ensure_page_loaded()

            # Get the HTML content
            content = await self.page.content()
            return content

        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return ""

    async def _ensure_page_loaded(self):
        """Ensure the page is fully loaded, handling dynamic content."""
        # Wait for network to be idle
        await self.page.wait_for_load_state('networkidle')

        # Scroll down to trigger lazy loading
        await self.page.evaluate("""
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
        """)

        # Wait a bit for any lazy-loaded content
        await asyncio.sleep(1)

        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0);")

    async def extract_data(self, html: str, selectors: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from HTML using the provided selectors.

        Args:
            html: HTML content
            selectors: Dictionary of selectors configuration

        Returns:
            Dict: Extracted data
        """
        if not selectors:
            # If no selectors provided, return the full HTML in markdown format
            if self.config.get('full_page', False):
                return {"full_content": self._html_to_markdown(html)}
            return {}

        soup = BeautifulSoup(html, 'html.parser')
        result = {}

        for key, selector_config in selectors.items():
            selector_type = selector_config['type']

            if selector_type == 'group':
                container_selector = selector_config['container']
                is_multiple = selector_config.get('multiple', False)
                fields = selector_config.get('fields', {})

                containers = soup.select(container_selector)

                if not containers:
                    result[key] = [] if is_multiple else None
                    continue

                items = []
                for container in containers:
                    item_data = {}
                    for field_key, field_selector in fields.items():
                        item_data[field_key] = self._extract_single_field(container, field_selector)
                    items.append(item_data)

                result[key] = items if is_multiple else (items[0] if items else None)

            else:
                result[key] = self._extract_single_field(soup, selector_config)

        return result

    def _extract_single_field(self, context, selector_config):
        """
        Extract a single field from the HTML context using the provided selector.

        Args:
            context: BeautifulSoup context
            selector_config: Configuration for the selector

        Returns:
            The extracted value
        """
        selector_type = selector_config['type']
        query = selector_config['query']
        attribute = selector_config.get('attribute')
        is_multiple = selector_config.get('multiple', False)

        if selector_type == 'css':
            elements = context.select(query)

            if not elements:
                return [] if is_multiple else None

            if is_multiple:
                if attribute:
                    return [elem.get(attribute) for elem in elements if elem.has_attr(attribute)]
                else:
                    return [elem.get_text(strip=True) for elem in elements]
            else:
                if attribute:
                    return elements[0].get(attribute) if elements[0].has_attr(attribute) else None
                else:
                    return elements[0].get_text(strip=True)

        elif selector_type == 'xpath':
            # BeautifulSoup doesn't natively support XPath,
            # this would require adding lxml integration
            # For simplicity, we'll focus on CSS selectors in this example
            return None

        return None

    def _html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to Markdown format.
        This is a simplified implementation - in a real scenario you would use
        a library like html2text or htmltab4

        Args:
            html: HTML content

        Returns:
            str: Markdown representation of the HTML
        """
        # In a real implementation, you'd use a library like html2text
        # For this example, we'll just return a placeholder
        soup = BeautifulSoup(html, 'html.parser')

        # Basic extraction of title and content
        title = soup.title.string if soup.title else "No Title"

        # Extract text from body
        body_text = soup.body.get_text(separator='\n', strip=True) if soup.body else ""

        return f"# {title}\n\n{body_text}"

    async def extract_with_playwright(self, selectors: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data directly using Playwright's selectors.
        This can be more reliable for JavaScript-rendered content.

        Args:
            selectors: Dictionary of selectors configuration

        Returns:
            Dict: Extracted data
        """
        result = {}

        for key, selector_config in selectors.items():
            selector_type = selector_config['type']

            if selector_type == 'group':
                container_selector = selector_config['container']
                is_multiple = selector_config.get('multiple', False)
                fields = selector_config.get('fields', {})

                # Get all container elements
                containers = await self.page.query_selector_all(container_selector)

                if not containers:
                    result[key] = [] if is_multiple else None
                    continue

                items = []
                for container in containers:
                    item_data = {}
                    for field_key, field_selector in fields.items():
                        item_data[field_key] = await self._extract_field_with_playwright(container, field_selector)
                    items.append(item_data)

                result[key] = items if is_multiple else (items[0] if items else None)

            else:
                result[key] = await self._extract_field_with_playwright(self.page, selector_config)

        return result

    async def _extract_field_with_playwright(self, context, selector_config):
        """
        Extract a field using Playwright's selector engine.

        Args:
            context: Playwright context (page or element handle)
            selector_config: Configuration for the selector

        Returns:
            The extracted value
        """
        selector_type = selector_config['type']
        query = selector_config['query']
        attribute = selector_config.get('attribute')
        is_multiple = selector_config.get('multiple', False)

        try:
            if selector_type == 'css':
                if is_multiple:
                    elements = await context.query_selector_all(query)

                    if not elements:
                        return []

                    results = []
                    for elem in elements:
                        if attribute:
                            attr_value = await elem.get_attribute(attribute)
                            results.append(attr_value)
                        else:
                            text = await elem.text_content()
                            results.append(text.strip())

                    return results
                else:
                    element = await context.query_selector(query)

                    if not element:
                        return None

                    if attribute:
                        return await element.get_attribute(attribute)
                    else:
                        text = await element.text_content()
                        return text.strip()

            elif selector_type == 'xpath':
                # Playwright supports XPath selectors directly
                # Just prefix the selector with "xpath="
                xpath_query = f"xpath={query}"

                if is_multiple:
                    elements = await context.query_selector_all(xpath_query)

                    if not elements:
                        return []

                    results = []
                    for elem in elements:
                        if attribute:
                            attr_value = await elem.get_attribute(attribute)
                            results.append(attr_value)
                        else:
                            text = await elem.text_content()
                            results.append(text.strip())

                    return results
                else:
                    element = await context.query_selector(xpath_query)

                    if not element:
                        return None

                    if attribute:
                        return await element.get_attribute(attribute)
                    else:
                        text = await element.text_content()
                        return text.strip()

        except Exception as e:
            logger.error(f"Error extracting field: {e}")
            return None if not is_multiple else []