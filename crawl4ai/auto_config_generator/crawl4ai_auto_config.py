#!/usr/bin/env python3
"""
Crawl4AI Auto Config Generator

This script provides a user-friendly way to automatically generate scraping
configurations for the Crawl4AI framework by opening a browser interface
that allows users to select elements visually.

Usage:
    python crawl4ai_auto_config.py --url https://example.com --output config.yaml
    python crawl4ai_auto_config.py --ui  # Start the web UI server
"""

import asyncio
import argparse
import os
import sys
import logging
import webbrowser
from typing import Dict, Any, Optional

# Import our modules
from crawl4ai.auto_config_generator.auto_config_generator import AutoConfigGenerator, ElementSelectorUI
from crawl4ai.auto_config_generator.browser_element_selector import BrowserElementSelector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('crawl4ai_auto_config')


async def generate_config_with_browser(url: str, output_path: Optional[str] = None,
                                       llm_api_key: Optional[str] = None,
                                       llm_provider: str = "anthropic",
                                       llm_model: str = "claude-3-haiku-20240307",
                                       debug: bool = False) -> Dict[str, Any]:
    """
    Generate a scraping configuration using a browser-based element selector.

    Args:
        url: URL to generate configuration for
        output_path: Optional path to save the configuration
        llm_api_key: Optional API key for LLM-powered selector optimization
        llm_provider: LLM provider to use
        llm_model: LLM model to use
        debug: Enable debugging

    Returns:
        Dict[str, Any]: Generated configuration
    """
    print(f"\n🔍 Opening browser for {url}...\n")

    try:
        # Initialize element selector
        async with BrowserElementSelector() as selector:
            # Load the page with debug if requested
            success = await selector.load_page(url, debug=debug)

            if not success:
                logger.error(f"Failed to load URL: {url}")
                return {}

            # Open the element selector
            print("\n📌 Please select elements to include in your scraping configuration.")
            print("   1. Click 'Select Element' in the toolbar (top right corner)")
            print("   2. Click on elements you want to extract (will be highlighted)")
            print("   3. Name each element and configure its properties")
            print("   4. When finished, click 'Generate Config' button")
            print("\n⏳ Waiting for your selections... (this window will update when done)")

            selections = await selector.open_element_selector()

            if not selections or len(selections) == 0:
                logger.warning("No elements were selected or config generation was cancelled")
                return {}

            print(f"\n✅ Selected {len(selections)} elements successfully!")

            # Create configuration from selections
            print("\n⚙️ Creating configuration from selections...")
            config = await selector.create_config_from_selections(selections)

            # Optionally optimize selectors with LLM
            if llm_api_key:
                print("\n🧠 Optimizing selectors with LLM...")

                # Initialize generator
                generator = AutoConfigGenerator(
                    llm_api_key=llm_api_key,
                    llm_provider=llm_provider,
                    llm_model=llm_model
                )

                # Optimize selectors
                config = await generator.generate_complete_config(url, config["extract"], optimize=True)

            # Save configuration if output path is provided
            if output_path:
                print(f"\n💾 Saving configuration to {output_path}...")
                await selector.save_config_to_file(config, output_path)
                print(f"Configuration saved successfully to {output_path}")

            return config

    except Exception as e:
        logger.error(f"Error generating configuration: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return {}


def start_ui_server(port: int = 8000):
    """
    Start the web UI server for configuration generation.

    Args:
        port: Port to run the server on
    """
    ui = ElementSelectorUI()
    ui.run(port=port)


async def main_async():
    """Async main function."""
    parser = argparse.ArgumentParser(description="Crawl4AI Automatic Configuration Generator")

    # Main options
    parser.add_argument("--url", help="URL to generate configuration for")
    parser.add_argument("--output", "-o", help="Path to save the generated configuration")
    parser.add_argument("--ui", action="store_true", help="Start the web UI server")
    parser.add_argument("--port", type=int, default=8000, help="Port for the web UI server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for troubleshooting")

    # LLM options
    parser.add_argument("--llm-key", help="API key for LLM service (for selector optimization)")
    parser.add_argument("--llm-provider", choices=["anthropic", "openai"], default="anthropic", help="LLM provider")
    parser.add_argument("--llm-model", default="claude-3-haiku-20240307", help="LLM model to use")

    args = parser.parse_args()

    # Set logging level based on debug mode
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")

    if args.ui:
        # Start the web UI server
        print(f"\n🚀 Starting Crawl4AI Configuration UI server on port {args.port}...")
        print(f"🌐 Open your browser at: http://localhost:{args.port}\n")
        start_ui_server(args.port)
    elif args.url:
        # Generate configuration using browser-based selector
        print(f"\n🚀 Starting browser-based configuration generator for {args.url}")
        print("This will open a browser window for you to select elements")

        config = await generate_config_with_browser(
            url=args.url,
            output_path=args.output,
            llm_api_key=args.llm_key,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            debug=args.debug
        )

        if not args.output and config:
            # Print configuration to console
            import yaml
            print("\n📋 Generated Configuration:")
            print("=" * 50)
            print(yaml.dump(config, default_flow_style=False))
            print("=" * 50)

            print("\nTo use this configuration, save it to a file and run:")
            print(f"python -m crawl4ai.main -c your_config.yaml")
    else:
        parser.print_help()


def main():
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()