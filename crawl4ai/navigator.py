import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from urllib.parse import urljoin, urlparse, parse_qs, urlunparse, urlencode

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('crawl4ai_navigator')


class Crawl4AINavigator:
    """
    Navigation manager for the Crawl4AI scraper.
    Handles pagination, URL construction, and structured navigation.
    """

    def __init__(self, scraper, config: Dict[str, Any]):
        """
        Initialize the navigator.

        Args:
            scraper: Instance of Crawl4AIScraper
            config: Dictionary containing navigation configuration
        """
        self.scraper = scraper
        self.config = config
        self.base_url = config['url']
        self.results = []

    async def paginate_and_scrape(self) -> List[Dict[str, Any]]:
        """
        Navigate through pages based on pagination configuration and scrape each page.

        Returns:
            List[Dict[str, Any]]: List of scraped data from all pages
        """
        pagination_config = self.config.get('pagination')
        selectors = self.config.get('extract', {})

        # If no pagination is configured, just scrape the base URL
        if not pagination_config:
            logger.info(f"No pagination configured, scraping single page: {self.base_url}")
            html = await self.scraper.navigate_to(self.base_url)

            if self.config.get('render_js', False):
                data = await self.scraper.extract_with_playwright(selectors)
            else:
                data = await self.scraper.extract_data(html, selectors)

            if data:
                self.results.append(data)

            return self.results

        # Configure pagination parameters
        param = pagination_config.get('param', 'page')
        start = pagination_config.get('start', 1)
        end = pagination_config.get('end', 1)
        step = pagination_config.get('step', 1)
        appender = pagination_config.get('appender', '&')

        # Paginate through the specified range
        for page_num in range(start, end + 1, step):
            page_url = self._construct_page_url(self.base_url, param, page_num, appender)
            logger.info(f"Navigating to page {page_num}: {page_url}")

            # Add a small delay between page requests to avoid being blocked
            if page_num > start:
                await asyncio.sleep(2)  # 2-second delay between pages

            # Navigate and scrape the page
            html = await self.scraper.navigate_to(page_url)

            if not html:
                logger.warning(f"Failed to get content from page {page_num}, skipping")
                continue

            # Extract data from the page
            if self.config.get('render_js', False):
                data = await self.scraper.extract_with_playwright(selectors)
            else:
                data = await self.scraper.extract_data(html, selectors)

            # Add page number to the data for reference
            if data:
                data['page_number'] = page_num
                self.results.append(data)

            # Check for early termination condition if configured
            if pagination_config.get('stop_if_empty', False) and (not data or self._is_empty_result(data)):
                logger.info(f"Stopping pagination at page {page_num} due to empty result")
                break

        return self.results

    def _construct_page_url(self, base_url: str, param: str, page_num: int, appender: str) -> str:
        """
        Construct the URL for a specific page based on the pagination configuration.

        Args:
            base_url: Base URL to start from
            param: Name of the pagination parameter
            page_num: Page number
            appender: Character used to append parameters

        Returns:
            str: Constructed URL for the specified page
        """
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query, keep_blank_values=True)

        # Add or update the pagination parameter
        query_params[param] = [str(page_num)]

        # Reconstruct the query string
        new_query = urlencode(query_params, doseq=True)

        # Construct the new URL with updated query parameters
        new_url_parts = list(parsed_url)
        new_url_parts[4] = new_query  # 4 is the query component

        return urlunparse(new_url_parts)

    def _is_empty_result(self, data: Dict[str, Any]) -> bool:
        """
        Check if the data result is effectively empty.

        Args:
            data: Extracted data

        Returns:
            bool: True if the result is empty, False otherwise
        """
        for key, value in data.items():
            if key == 'page_number':
                continue

            if isinstance(value, list) and value:
                return False
            elif isinstance(value, dict) and value:
                return False
            elif value:
                return False

        return True

    async def navigate_through_links(self, link_selector: str, max_links: int = 10,
                                     data_processor: Optional[
                                         Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None) -> List[
        Dict[str, Any]]:
        """
        Navigate through a series of links found on the base page.

        Args:
            link_selector: CSS selector to find links
            max_links: Maximum number of links to follow
            data_processor: Optional callback function to process data from each linked page

        Returns:
            List[Dict[str, Any]]: List of scraped data from all linked pages
        """
        # Navigate to the base URL first
        base_html = await self.scraper.navigate_to(self.base_url)
        if not base_html:
            logger.error("Failed to load base URL")
            return []

        # Extract links from the base page
        link_configs = {'links': {'type': 'css', 'query': link_selector, 'attribute': 'href', 'multiple': True}}
        link_data = await self.scraper.extract_data(base_html, link_configs)

        links = link_data.get('links', [])
        if not links:
            logger.warning(f"No links found with selector: {link_selector}")
            return []

        # Limit the number of links to follow
        links = links[:max_links]

        results = []
        for i, link in enumerate(links):
            # Construct absolute URL if the link is relative
            if not link.startswith(('http://', 'https://')):
                link = urljoin(self.base_url, link)

            logger.info(f"Following link {i + 1}/{len(links)}: {link}")

            # Add a delay between requests
            if i > 0:
                await asyncio.sleep(2)

            # Navigate to the linked page
            link_html = await self.scraper.navigate_to(link)
            if not link_html:
                logger.warning(f"Failed to load content from link: {link}")
                continue

            # Process the linked page
            if data_processor:
                # Use the provided data processor function
                link_data = await data_processor(link_html, self.config.get('extract', {}))
            else:
                # Use default extraction
                if self.config.get('render_js', False):
                    link_data = await self.scraper.extract_with_playwright(self.config.get('extract', {}))
                else:
                    link_data = await self.scraper.extract_data(link_html, self.config.get('extract', {}))

            # Add the URL to the data for reference
            if link_data:
                link_data['url'] = link
                results.append(link_data)

        return results

    async def navigate_api_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Navigate through a series of API endpoints.

        Args:
            endpoints: List of endpoint configurations with URL and method

        Returns:
            List[Dict[str, Any]]: List of API responses
        """
        results = []

        for endpoint in endpoints:
            url = endpoint.get('url')

            if not url:
                logger.warning("Skipping endpoint with no URL")
                continue

            # Construct absolute URL if the endpoint URL is relative
            if not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)

            logger.info(f"Calling API endpoint: {url}")

            # Use the page.goto method for GET requests, but this could be extended
            # to support other HTTP methods using fetch or other API
            response_html = await self.scraper.navigate_to(url)

            # Try to parse the response as JSON
            try:
                import json
                response_data = json.loads(response_html)
                results.append(response_data)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response from endpoint: {url}")
                # Store the raw response instead
                results.append({"url": url, "raw_response": response_html})

        return results