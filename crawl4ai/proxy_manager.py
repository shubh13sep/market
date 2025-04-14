import random
import time
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple, Any
import json
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proxy_manager')


class ProxyManager:
    """
    Manages a pool of proxies, including rotation, testing, and tracking usage metrics.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the proxy manager with configuration.

        Args:
            config: Dictionary containing proxy configuration
        """
        self.config = config
        self.proxy_list = []
        self.current_index = 0
        self.proxy_stats = {}
        self.rotation_strategy = config.get('rotation_strategy', 'round_robin')  # or 'random', 'performance'
        self.test_url = config.get('test_url', 'https://httpbin.org/ip')
        self.max_failures = config.get('max_failures', 3)
        self.min_delay_between_rotations = config.get('min_delay_between_rotations', 10)  # seconds
        self.last_rotation_time = 0
        self.proxy_file = config.get('proxy_file', None)
        self.proxy_api_url = config.get('proxy_api_url', None)
        self.proxy_api_key = config.get('proxy_api_key', None)
        self.proxy_auth = config.get('proxy_auth', None)

        # Initialize the proxy list
        self._load_proxies()

    def _load_proxies(self) -> None:
        """Load proxies from file, API, or direct configuration."""
        # Method 1: Load from direct configuration
        if 'proxies' in self.config:
            self.proxy_list = self.config['proxies']
            logger.info(f"Loaded {len(self.proxy_list)} proxies from configuration")

        # Method 2: Load from a file
        elif self.proxy_file and os.path.exists(self.proxy_file):
            try:
                with open(self.proxy_file, 'r') as f:
                    if self.proxy_file.endswith('.json'):
                        self.proxy_list = json.load(f)
                    else:
                        # Assume text file with one proxy per line
                        self.proxy_list = [line.strip() for line in f.readlines() if line.strip()]
                logger.info(f"Loaded {len(self.proxy_list)} proxies from file {self.proxy_file}")
            except Exception as e:
                logger.error(f"Error loading proxies from file: {e}")
                self.proxy_list = []

        # Method 3: Load from a proxy API
        elif self.proxy_api_url:
            asyncio.run(self._load_proxies_from_api())

        # Initialize statistics for each proxy
        for proxy in self.proxy_list:
            proxy_id = self._get_proxy_id(proxy)
            self.proxy_stats[proxy_id] = {
                'success_count': 0,
                'failure_count': 0,
                'last_used': 0,
                'average_response_time': 0,
                'banned': False
            }

    async def _load_proxies_from_api(self) -> None:
        """Load proxies from an API endpoint."""
        try:
            headers = {}
            if self.proxy_api_key:
                headers['Authorization'] = f'Bearer {self.proxy_api_key}'

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(self.proxy_api_url) as response:
                    if response.status == 200:
                        data = await response.json()

                        # The exact format depends on your proxy provider's API
                        if isinstance(data, list):
                            self.proxy_list = data
                        elif isinstance(data, dict) and 'proxies' in data:
                            self.proxy_list = data['proxies']
                        elif isinstance(data, dict) and 'data' in data:
                            self.proxy_list = data['data']
                        else:
                            logger.error(f"Unexpected API response format: {data}")
                            self.proxy_list = []

                        logger.info(f"Loaded {len(self.proxy_list)} proxies from API")
                    else:
                        logger.error(f"Error loading proxies from API: {response.status}")
                        self.proxy_list = []
        except Exception as e:
            logger.error(f"Exception loading proxies from API: {e}")
            self.proxy_list = []

    def _get_proxy_id(self, proxy: Dict[str, str] or str) -> str:
        """Get a unique identifier for a proxy."""
        if isinstance(proxy, dict):
            return f"{proxy.get('host')}:{proxy.get('port')}"
        return str(proxy)

    def _format_proxy_url(self, proxy: Dict[str, str] or str) -> str:
        """Format a proxy into a URL string for use with requests."""
        if isinstance(proxy, dict):
            host = proxy.get('host', '')
            port = proxy.get('port', '')
            username = proxy.get('username', '')
            password = proxy.get('password', '')

            if username and password:
                return f"http://{username}:{password}@{host}:{port}"
            else:
                return f"http://{host}:{port}"
        return proxy  # Assume it's already formatted correctly

    def _get_playwright_proxy(self, proxy: Dict[str, str] or str) -> Dict[str, Any]:
        """Format a proxy for use with Playwright."""
        if isinstance(proxy, dict):
            result = {
                'server': f"http://{proxy.get('host')}:{proxy.get('port')}"
            }

            if proxy.get('username') and proxy.get('password'):
                result['username'] = proxy.get('username')
                result['password'] = proxy.get('password')

            return result
        elif isinstance(proxy, str):
            # Try to parse the proxy string
            # Format: http://username:password@host:port or host:port
            if '@' in proxy:
                auth, address = proxy.split('@')
                if '://' in auth:
                    _, auth = auth.split('://', 1)
                username, password = auth.split(':')
                return {
                    'server': f"http://{address}",
                    'username': username,
                    'password': password
                }
            else:
                if '://' in proxy:
                    return {'server': proxy}
                else:
                    return {'server': f"http://{proxy}"}

        return {'server': str(proxy)}

    def get_next_proxy(self, for_playwright: bool = False) -> Dict[str, str] or str or None:
        """
        Get the next proxy based on the rotation strategy.

        Args:
            for_playwright: Whether the proxy is for Playwright (returns different format)

        Returns:
            The next proxy to use, or None if no proxies are available
        """
        if not self.proxy_list:
            return None

        # Ensure minimum delay between rotations
        current_time = time.time()
        if current_time - self.last_rotation_time < self.min_delay_between_rotations:
            logger.debug("Waiting for minimum delay between rotations")
            time.sleep(self.min_delay_between_rotations - (current_time - self.last_rotation_time))

        self.last_rotation_time = time.time()

        # Filter out banned proxies
        active_proxies = [p for p in self.proxy_list if not self.proxy_stats[self._get_proxy_id(p)]['banned']]

        if not active_proxies:
            logger.warning("No active proxies available")
            # Reset banned status if all proxies are banned
            for proxy_id in self.proxy_stats:
                self.proxy_stats[proxy_id]['banned'] = False
            active_proxies = self.proxy_list

        # Choose proxy based on strategy
        if self.rotation_strategy == 'random':
            proxy = random.choice(active_proxies)
        elif self.rotation_strategy == 'performance':
            # Sort by success rate and response time
            def score_proxy(p):
                stats = self.proxy_stats[self._get_proxy_id(p)]
                success_rate = stats['success_count'] / max(1, stats['success_count'] + stats['failure_count'])
                response_time = stats['average_response_time'] or 1000  # Default high value if no data
                return success_rate / (response_time * 0.001)  # Higher score is better

            active_proxies.sort(key=score_proxy, reverse=True)  # Highest score first
            proxy = active_proxies[0]
        else:  # 'round_robin'
            self.current_index = (self.current_index + 1) % len(active_proxies)
            proxy = active_proxies[self.current_index]

        # Update usage stats
        proxy_id = self._get_proxy_id(proxy)
        self.proxy_stats[proxy_id]['last_used'] = time.time()

        if for_playwright:
            return self._get_playwright_proxy(proxy)
        return self._format_proxy_url(proxy) if self.config.get('format_url', True) else proxy

    async def test_proxies(self) -> None:
        """Test all proxies to update performance metrics."""
        logger.info("Testing all proxies...")

        async def test_single_proxy(proxy):
            proxy_id = self._get_proxy_id(proxy)
            proxy_url = self._format_proxy_url(proxy)
            start_time = time.time()

            try:
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=10)  # 10 sec timeout
                    async with session.get(
                            self.test_url,
                            proxy=proxy_url,
                            timeout=timeout
                    ) as response:
                        if response.status == 200:
                            duration = time.time() - start_time
                            # Update stats with exponential moving average (EMA)
                            alpha = 0.3  # Weight for new data point
                            if self.proxy_stats[proxy_id]['average_response_time'] == 0:
                                self.proxy_stats[proxy_id]['average_response_time'] = duration
                            else:
                                self.proxy_stats[proxy_id]['average_response_time'] = (
                                        alpha * duration +
                                        (1 - alpha) * self.proxy_stats[proxy_id]['average_response_time']
                                )
                            self.proxy_stats[proxy_id]['success_count'] += 1
                            return True
                        else:
                            self.proxy_stats[proxy_id]['failure_count'] += 1
                            return False
            except Exception as e:
                logger.debug(f"Proxy test failed for {proxy_id}: {e}")
                self.proxy_stats[proxy_id]['failure_count'] += 1
                return False

        # Test all proxies concurrently
        tasks = []
        for proxy in self.proxy_list:
            tasks.append(asyncio.create_task(test_single_proxy(proxy)))

        results = await asyncio.gather(*tasks)
        logger.info(f"Proxy test completed: {sum(results)} working, {len(results) - sum(results)} failed")

        # Check for proxies to ban
        for proxy in self.proxy_list:
            proxy_id = self._get_proxy_id(proxy)
            if self.proxy_stats[proxy_id]['failure_count'] >= self.max_failures:
                logger.warning(f"Banning proxy {proxy_id} due to multiple failures")
                self.proxy_stats[proxy_id]['banned'] = True

    def report_success(self, proxy: Dict[str, str] or str) -> None:
        """Report a successful request with the given proxy."""
        if not proxy:
            return

        proxy_id = self._get_proxy_id(proxy)
        if proxy_id in self.proxy_stats:
            self.proxy_stats[proxy_id]['success_count'] += 1

    def report_failure(self, proxy: Dict[str, str] or str) -> None:
        """Report a failed request with the given proxy."""
        if not proxy:
            return

        proxy_id = self._get_proxy_id(proxy)
        if proxy_id in self.proxy_stats:
            self.proxy_stats[proxy_id]['failure_count'] += 1

            # Ban proxy if it has too many failures
            if self.proxy_stats[proxy_id]['failure_count'] >= self.max_failures:
                logger.warning(f"Banning proxy {proxy_id} due to multiple failures")
                self.proxy_stats[proxy_id]['banned'] = True

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for all proxies."""
        return self.proxy_stats

    def save_stats(self, file_path: str = "proxy_stats.json") -> None:
        """Save proxy statistics to a file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.proxy_stats, f, indent=2)
            logger.info(f"Proxy statistics saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving proxy statistics: {e}")