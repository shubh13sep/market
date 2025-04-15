import asyncio
import argparse
import logging
import os
import sys
from typing import Dict, Any, List, Optional

# Import our modules
from crawl4ai.config_loader import Crawl4AIConfigLoader
from crawl4ai.crawl4ai_scraper import Crawl4AIScraper
from crawl4ai.navigator import Crawl4AINavigator
from crawl4ai.output_generator import Crawl4AIOutputGenerator
from crawl4ai.proxy_manager import ProxyManager
from crawl4ai.llm_selector_generator import LLMSelectorGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawl4ai.log')
    ]
)
logger = logging.getLogger('crawl4ai')


async def run_scraper(config_path: str, output_file: Optional[str] = None, url_override: Optional[str] = None) -> str:
    """
    Run the Crawl4AI scraper with the specified configuration.

    Args:
        config_path: Path to the configuration file
        output_file: Optional output file name
        url_override: Optional URL to override the one in the config

    Returns:
        str: Path to the output file
    """
    try:
        # Load configuration
        logger.info(f"Loading configuration from {config_path}")
        config_loader = Crawl4AIConfigLoader(config_path)
        config = config_loader.get_config()

        # Override URL if provided
        if url_override:
            logger.info(f"Overriding URL from command line: {url_override}")
            config['url'] = url_override

        # Initialize proxy manager if enabled
        proxy_manager = None
        if config.get('proxy', {}).get('enabled', False):
            logger.info("Initializing proxy manager")
            proxy_manager = ProxyManager(config.get('proxy', {}))

            # Test proxies if configured
            if config.get('proxy', {}).get('test_on_start', True):
                await proxy_manager.test_proxies()

        # Initialize LLM selector generator if enabled
        llm_selector_generator = None
        if config.get('llm_selectors', {}).get('enabled', False):
            logger.info("Initializing LLM selector generator")
            llm_selector_generator = LLMSelectorGenerator(config.get('llm_selectors', {}))

        # Adjust scraper options for proxy if needed
        scraper_options = config.copy()
        if proxy_manager:
            # Get proxy for Playwright
            proxy_config = proxy_manager.get_next_proxy(for_playwright=True)
            if proxy_config:
                scraper_options['proxy'] = proxy_config
                logger.info(f"Using proxy: {proxy_config.get('server')}")

        # Initialize the scraper
        async with Crawl4AIScraper(scraper_options) as scraper:
            # Perform login if configured
            login_config = config_loader.get_login_config()
            if login_config:
                logger.info("Logging in...")
                success = await scraper.login(login_config)
                if not success:
                    logger.error("Login failed, aborting")
                    return ""

            # Initialize the navigator
            navigator = Crawl4AINavigator(scraper, config)

            # Check if we need to generate selectors using LLM
            if llm_selector_generator and config.get('llm_selectors', {}).get('generate_on_start', False):
                # First, load the page to get the HTML content
                logger.info("Loading page to generate selectors with LLM")
                html = await scraper.navigate_to(config['url'])

                if not html:
                    logger.error("Failed to load page for selector generation, aborting")
                    return ""

                # Generate selectors based on extraction configuration
                extraction_spec = config.get('extraction_spec', {})
                if extraction_spec:
                    logger.info("Generating selectors with LLM based on extraction spec")
                    selectors = await llm_selector_generator.create_full_extraction_config(
                        config['url'], html, extraction_spec
                    )

                    if selectors:
                        # Update the config with the generated selectors
                        logger.info(f"Generated {len(selectors)} selectors with LLM")
                        config['extract'] = selectors

                        # Test the selectors
                        logger.info("Testing generated selectors")
                        test_results = await llm_selector_generator.test_selectors(html, selectors)
                        failed_count = sum(1 for result in test_results.values() if not result)

                        if failed_count > 0:
                            logger.warning(f"{failed_count} selectors failed testing, attempting refinement")
                            refined_selectors = await llm_selector_generator.refine_selectors(
                                config['url'], html, selectors, test_results
                            )
                            config['extract'] = refined_selectors

            # Scrape data based on the navigation type
            navigation_type = config.get('navigation_type', 'pagination')

            if navigation_type == 'pagination':
                # Paginate through results
                logger.info("Starting pagination-based scraping")
                results = await navigator.paginate_and_scrape()
            elif navigation_type == 'links':
                # Follow links from the base page
                logger.info("Starting link-following scraping")
                link_selector = config.get('link_selector', 'a')
                max_links = config.get('max_links', 10)
                results = await navigator.navigate_through_links(link_selector, max_links)
            elif navigation_type == 'api':
                # Call API endpoints
                logger.info("Starting API endpoint scraping")
                endpoints = config.get('endpoints', [])
                results = await navigator.navigate_api_endpoints(endpoints)
            else:
                # Default to single page scraping
                logger.info("Starting single page scraping")
                # If we already loaded the page for selector generation, reuse that HTML
                if not html:
                    html = await scraper.navigate_to(config['url'])

                if config.get('render_js', False):
                    data = await scraper.extract_with_playwright(config.get('extract', {}))
                else:
                    data = await scraper.extract_data(html, config.get('extract', {}))
                results = [data] if data else []

            # Process and save the results
            output_generator = Crawl4AIOutputGenerator(config)

            if config.get('merge_results', True) and results:
                # Merge multiple result sets into one
                merged_results = output_generator.merge_results(results)
                output_path = output_generator.generate_output(merged_results, output_file)
            else:
                # Save results as a list
                output_path = output_generator.generate_output(results, output_file)

            # Save proxy statistics if we used proxies
            if proxy_manager:
                proxy_manager.save_stats()

            return output_path

    except Exception as e:
        logger.error(f"Error running scraper: {e}", exc_info=True)
        return ""

#Sample Execution Command: python main.py -c Configs/Scraping/screener.yaml
def main():
    """Main entry point for the Crawl4AI scraper."""
    parser = argparse.ArgumentParser(description='Crawl4AI - A powerful web scraping framework')
    parser.add_argument('-c', '--config', required=True, help='Path to YAML/JSON configuration file')
    parser.add_argument('-o', '--output', help='Output file name (default: auto-generated)')
    parser.add_argument('-u', '--url', help='Override URL from config file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--proxy', action='store_true', help='Enable proxy rotation even if disabled in config')
    parser.add_argument('--llm', action='store_true', help='Enable LLM selector generation even if disabled in config')
    parser.add_argument('--proxy-file', help='Path to proxy list file, overrides config')
    parser.add_argument('--llm-key', help='API key for LLM service, overrides config')
    parser.add_argument('--test-selectors', action='store_true',
                        help='Test selectors and display results without scraping')

    args = parser.parse_args()

    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load the config to modify it based on command line arguments
    try:
        config_loader = Crawl4AIConfigLoader(args.config)
        config = config_loader.get_config()

        # Apply command line overrides
        if args.proxy:
            if 'proxy' not in config:
                config['proxy'] = {}
            config['proxy']['enabled'] = True

        if args.proxy_file:
            if 'proxy' not in config:
                config['proxy'] = {}
            config['proxy']['enabled'] = True
            config['proxy']['proxy_file'] = args.proxy_file

        if args.llm:
            if 'llm_selectors' not in config:
                config['llm_selectors'] = {}
            config['llm_selectors']['enabled'] = True
            config['llm_selectors']['generate_on_start'] = True

        if args.llm_key:
            if 'llm_selectors' not in config:
                config['llm_selectors'] = {}
            config['llm_selectors']['llm_api_key'] = args.llm_key

        # Save modified config if needed
        if args.proxy or args.proxy_file or args.llm or args.llm_key:
            modified_config_path = f"{os.path.splitext(args.config)[0]}_modified.yaml"
            with open(modified_config_path, 'w') as f:
                import yaml
                yaml.dump(config, f)
            logger.info(f"Saved modified configuration to {modified_config_path}")
            args.config = modified_config_path

        # Run the scraper
        output_path = asyncio.run(run_scraper(args.config, args.output, args.url))

        if output_path:
            print(f"\nScraping completed successfully! Output saved to:\n{output_path}")
            return 0
        else:
            print("\nScraping failed. Check the logs for details.")
            return 1

    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())