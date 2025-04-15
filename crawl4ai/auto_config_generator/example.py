"""
Crawl4AI Usage Example

This example demonstrates how to use Crawl4AI with automatically generated configurations
to scrape data from websites.
"""

import asyncio
import os
import json
import yaml
from pprint import pprint

# Import Crawl4AI modules
from crawl4ai.crawl4ai_scraper import Crawl4AIScraper
from crawl4ai.output_generator import Crawl4AIOutputGenerator
from crawl4ai.auto_config_generator.auto_config_generator import AutoConfigGenerator


async def scrape_with_auto_config():
    """Example of scraping a site using automatic configuration generation."""
    print("\n=== Scraping with Auto-Generated Configuration ===\n")

    # The URL to scrape
    url = "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"

    # Step 1: Generate configuration automatically
    print(f"Generating configuration for {url}...")

    generator = AutoConfigGenerator()

    # Capture headers
    await generator.capture_headers(url)

    # Define what we want to extract
    extraction_spec = {
        "book_list": {
            # Fields within each book item
            "title": None,
            "price": None,
            "rating": None,
            "image": None,
            "link": None
        }
    }

    # Create configuration
    config = await generator.generate_complete_config(url, extraction_spec, optimize=True)

    # Print the generated configuration
    print("\nGenerated Configuration:")
    print("-" * 40)
    print(yaml.dump(config, default_flow_style=False))
    print("-" * 40)

    # Step 2: Use the configuration to scrape data
    print("\nScraping data...")

    # Save configuration to file
    config_path = "auto_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Initialize scraper with config
    async with Crawl4AIScraper(config) as scraper:
        # Navigate to URL
        html = await scraper.navigate_to(url)

        # Extract data using config
        data = await scraper.extract_data(html, config["extract"])

        # Print results
        print("\nScraped Data:")
        print("-" * 40)
        pprint(data)
        print("-" * 40)

        # Save results
        output_generator = Crawl4AIOutputGenerator(config)
        output_path = output_generator.generate_output(data, "books_mystery.json")

        print(f"\nData saved to {output_path}")

    print("\nDone!")


async def example_interactive_scraping():
    """
    Example demonstrating how to use the interactive browser-based selector
    to generate a scraping configuration.

    This would normally be run through the command-line tool
    but is included here for demonstration.
    """
    from crawl4ai.auto_config_generator.browser_element_selector import BrowserElementSelector

    url = "https://news.ycombinator.com/"

    print(f"\n=== Interactive Scraping for {url} ===\n")
    print("This will open a browser window for you to select elements...")
    print("Instructions:")
    print("1. Click 'Select Element' in the toolbar (top right)")
    print("2. Click on elements you want to extract (like post titles, points, etc.)")
    print("3. Name each element and configure its properties")
    print("4. When done selecting, click 'Generate Config'")
    print("5. The config will automatically be used to scrape the site")

    # Wait a moment to allow the user to read the message
    await asyncio.sleep(3)

    try:
        async with BrowserElementSelector() as selector:
            # Load the page
            success = await selector.load_page(url)

            if not success:
                print(f"Failed to load URL: {url}")
                return

            print("\nPage loaded successfully. Waiting for you to select elements...")

            # Open selector in browser
            selections = await selector.open_element_selector()

            if selections and len(selections) > 0:
                print(f"\nReceived {len(selections)} element selections!")

                # Generate config from selections
                config = await selector.create_config_from_selections(selections)

                print("\nGenerated Configuration:")
                print("-" * 40)
                print(yaml.dump(config, default_flow_style=False))

                # Save configuration to file
                config_file = "interactive_config.yaml"
                await selector.save_config_to_file(config, config_file)
                print(f"\nSaved configuration to {config_file}")

                # Use the configuration to scrape
                print("\nScraping with generated configuration...")

                async with Crawl4AIScraper(config) as scraper:
                    html = await scraper.navigate_to(url)

                    if not html:
                        print("Failed to load page for scraping.")
                        return

                    # Extract data using the configuration
                    if config.get("render_js", False):
                        data = await scraper.extract_with_playwright(config["extract"])
                    else:
                        data = await scraper.extract_data(html, config["extract"])

                    print("\nScraped Data:")
                    print("-" * 40)
                    pprint(data)

                    # Save the scraped data
                    output_generator = Crawl4AIOutputGenerator(config)
                    output_path = output_generator.generate_output(data, "scraped_data.json")
                    print(f"\nSaved scraped data to {output_path}")
            else:
                print("No elements were selected or config generation was cancelled.")
    except Exception as e:
        print(f"Error during interactive scraping: {e}")


async def main():
    """Main function to run the examples."""
    # Example of scraping with auto-generated configuration
    #await scrape_with_auto_config()

    # Uncomment to run the interactive example
    # This will open a browser window
    await example_interactive_scraping()


if __name__ == "__main__":
    asyncio.run(main())