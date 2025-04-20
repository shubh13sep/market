import asyncio
import json
import yaml
import os
import logging
import re
import argparse
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

# Import our modules
from crawl4ai.crawl4ai_scraper import Crawl4AIScraper
from crawl4ai.auto_config_generator.llm_selector_generator import LLMSelectorGenerator
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('config_generator')


class ConfigGenerator:
    """
    Hybrid configuration generator that combines templates, LLM analysis,
    and validation to create optimal scraping configurations.
    """

    def __init__(self, llm_api_key: Optional[str] = None,
                 llm_provider: str = "anthropic",
                 llm_model: str = "claude-3-haiku-20240307"):
        """
        Initialize the configuration generator.

        Args:
            llm_api_key: API key for the LLM service
            llm_provider: LLM provider to use ("anthropic" or "openai")
            llm_model: Model to use
        """
        self.llm_api_key = self.llm_api_key = llm_api_key or self._get_api_key_from_env(llm_provider)
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")

        # Create templates directory if it doesn't exist
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            self._create_default_templates()

    def _get_api_key_from_env(self, provider: str) -> Optional[str]:
        """Get the appropriate API key from environment variables based on provider."""
        if provider == "anthropic":
            return os.environ.get('ANTHROPIC_API_KEY')
        elif provider == "openai":
            return os.environ.get('OPENAI_API_KEY')
        elif provider == "google":
            return os.environ.get('GOOGLE_API_KEY')
        else:
            return None

    def _create_default_templates(self):
        """Create default templates for common website types."""
        templates = {
            "e-commerce_product.yaml": {
                "url": "",
                "render_js": True,
                "stealth_mode": True,
                "navigation_type": "single",
                "extract": {
                    "title": {"type": "css", "query": "h1.product-title", "multiple": False},
                    "price": {"type": "css", "query": "span.price", "multiple": False},
                    "description": {"type": "css", "query": "div.product-description", "multiple": False},
                    "images": {"type": "css", "query": "img.product-image", "attribute": "src", "multiple": True},
                    "rating": {"type": "css", "query": "div.rating", "multiple": False},
                    "reviews": {"type": "css", "query": "div.review-text", "multiple": True}
                },
                "output_format": "json"
            },
            "e-commerce_listing.yaml": {
                "url": "",
                "render_js": True,
                "stealth_mode": True,
                "navigation_type": "pagination",
                "pagination": {
                    "param": "page",
                    "start": 1,
                    "end": 5,
                    "step": 1
                },
                "extract": {
                    "products": {
                        "type": "group",
                        "multiple": True,
                        "container": "div.product-card",
                        "fields": {
                            "name": {"type": "css", "query": "h3.product-name", "multiple": False},
                            "price": {"type": "css", "query": "span.price", "multiple": False},
                            "url": {"type": "css", "query": "a.product-link", "attribute": "href", "multiple": False},
                            "image": {"type": "css", "query": "img.product-image", "attribute": "src",
                                      "multiple": False}
                        }
                    }
                },
                "output_format": "json"
            },
            "news_article.yaml": {
                "url": "",
                "render_js": True,
                "stealth_mode": True,
                "navigation_type": "single",
                "extract": {
                    "title": {"type": "css", "query": "h1.article-title", "multiple": False},
                    "author": {"type": "css", "query": "span.author-name", "multiple": False},
                    "published_date": {"type": "css", "query": "time.publish-date", "multiple": False},
                    "content": {"type": "css", "query": "div.article-body", "multiple": False},
                    "tags": {"type": "css", "query": "a.tag", "multiple": True}
                },
                "output_format": "markdown"
            },
            "news_listing.yaml": {
                "url": "",
                "render_js": True,
                "stealth_mode": True,
                "navigation_type": "links",
                "link_selector": "a.article-title",
                "max_links": 20,
                "extract": {
                    "articles": {
                        "type": "group",
                        "multiple": True,
                        "container": "div.article-card",
                        "fields": {
                            "title": {"type": "css", "query": "h2.article-title", "multiple": False},
                            "snippet": {"type": "css", "query": "p.article-snippet", "multiple": False},
                            "url": {"type": "css", "query": "a.article-link", "attribute": "href", "multiple": False},
                            "date": {"type": "css", "query": "span.publish-date", "multiple": False}
                        }
                    }
                },
                "output_format": "json"
            },
            "api_endpoint.yaml": {
                "url": "",
                "navigation_type": "api",
                "endpoints": [
                    {
                        "url": "",
                        "method": "GET",
                        "params": {}
                    }
                ],
                "parse_json": True,
                "output_format": "json"
            }
        }

        for filename, template in templates.items():
            filepath = os.path.join(self.templates_dir, filename)
            with open(filepath, 'w') as f:
                yaml.dump(template, f, default_flow_style=False)

            logger.info(f"Created template: {filepath}")

    async def detect_site_type(self, url: str) -> str:
        """
        Detect the type of website based on the URL and page content.

        Args:
            url: URL to analyze

        Returns:
            str: Detected site type
        """
        # Initialize scraper with minimal configuration
        config = {
            "url": url,
            "render_js": True
        }

        site_type = "unknown"

        try:
            async with Crawl4AIScraper(config) as scraper:
                # Load the page
                html = await scraper.navigate_to(url)
                if not html:
                    logger.error(f"Failed to load URL: {url}")
                    return site_type

                # Use BeautifulSoup to analyze page structure
                soup = BeautifulSoup(html, 'html.parser')

                # Check URL patterns
                parsed_url = urlparse(url)
                hostname = parsed_url.hostname or ""
                path = parsed_url.path or ""

                # E-commerce patterns
                ecommerce_domains = ["shop", "store", "amazon", "ebay", "etsy", "walmart", "product"]
                ecommerce_paths = ["/product", "/item", "/p/", "/shop", "/catalog"]

                # News patterns
                news_domains = ["news", "article", "blog", "post", "times", "herald", "journal"]
                news_paths = ["/article", "/story", "/news", "/blog", "/post"]

                # API patterns
                api_patterns = ["/api", "/v1", "/v2", "/graphql", "/data", "/json"]

                # Check domain patterns
                for pattern in ecommerce_domains:
                    if pattern in hostname.lower():
                        # Check if it's a product page or listing page
                        if any(p in path.lower() for p in ["/product", "/item", "/p/"]):
                            site_type = "e-commerce_product"
                            break
                        else:
                            site_type = "e-commerce_listing"
                            break

                if site_type == "unknown":
                    for pattern in news_domains:
                        if pattern in hostname.lower():
                            # Check if it's an article page or listing page
                            if any(p in path.lower() for p in ["/article", "/story", "/post/"]):
                                site_type = "news_article"
                                break
                            else:
                                site_type = "news_listing"
                                break

                if site_type == "unknown":
                    for pattern in api_patterns:
                        if pattern in path.lower():
                            site_type = "api_endpoint"
                            break

                # If URL analysis didn't work, analyze HTML structure
                if site_type == "unknown":
                    # Check for e-commerce patterns
                    product_indicators = [
                        soup.find("div", {"id": re.compile(r"product", re.I)}),
                        soup.find("div", {"class": re.compile(r"product", re.I)}),
                        soup.find(["button", "a"], text=re.compile(r"add to cart|buy now", re.I)),
                        soup.find(string=re.compile(r"product details|specifications", re.I))
                    ]

                    if any(indicator for indicator in product_indicators):
                        site_type = "e-commerce_product"
                    else:
                        # Check for product listing patterns
                        listing_indicators = [
                            len(soup.find_all("div", {"class": re.compile(r"product|item|card", re.I)})) > 5,
                            len(soup.find_all("li", {"class": re.compile(r"product|item|card", re.I)})) > 5,
                            soup.find("div", {"id": re.compile(r"products|catalog|search-results", re.I)})
                        ]

                        if any(listing_indicators):
                            site_type = "e-commerce_listing"

                    # Check for news article patterns
                    article_indicators = [
                        soup.find("article"),
                        soup.find(["h1", "h2"], {"class": re.compile(r"headline|title", re.I)}),
                        soup.find(["div", "span"], {"class": re.compile(r"author|byline", re.I)}),
                        soup.find(["div", "section"], {"class": re.compile(r"article-body|content", re.I)})
                    ]

                    if any(indicator for indicator in article_indicators) and site_type == "unknown":
                        site_type = "news_article"

                    # Check for news listing patterns
                    news_listing_indicators = [
                        len(soup.find_all("article")) > 3,
                        len(soup.find_all("div", {"class": re.compile(r"headline|article|story", re.I)})) > 3,
                        soup.find("div", {"id": re.compile(r"headlines|news|latest", re.I)})
                    ]

                    if any(news_listing_indicators) and site_type == "unknown":
                        site_type = "news_listing"

                logger.info(f"Detected site type for {url}: {site_type}")
                return site_type

        except Exception as e:
            logger.error(f"Error detecting site type: {e}")
            return "unknown"

    async def load_template(self, site_type: str) -> Dict[str, Any]:
        """
        Load a template configuration based on site type.

        Args:
            site_type: Type of website

        Returns:
            Dict: Template configuration
        """
        template_file = os.path.join(self.templates_dir, f"{site_type}.yaml")

        if os.path.exists(template_file):
            with open(template_file, 'r') as f:
                template = yaml.safe_load(f)
                logger.info(f"Loaded template for {site_type}")
                return template
        else:
            logger.warning(f"No template found for {site_type}, using generic template")
            # Fallback to a minimal template
            return {
                "url": "",
                "render_js": True,
                "extract": {},
                "output_format": "json"
            }

    async def enhance_with_llm(self, url: str, config: Dict[str, Any], html: str) -> Dict[str, Any]:
        """
        Enhance configuration using LLM to analyze page structure and generate selectors.

        Args:
            url: URL of the page
            config: Initial configuration
            html: HTML content of the page

        Returns:
            Dict: Enhanced configuration
        """
        # Initialize LLM selector generator
        llm_config = {
            "enabled": True,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_api_key": self.llm_api_key,
            "use_cache": True
        }
        selector_generator = LLMSelectorGenerator(llm_config)

        # Create extraction specification based on the template config
        extraction_spec = {}
        for key, value in config.get("extract", {}).items():
            if value.get("type") == "group":
                # For group selectors, extract field names
                extraction_spec[key] = list(value.get("fields", {}).keys())
            else:
                # For simple selectors, just add the key
                extraction_spec[key] = None

        # Use LLM to generate selectors
        logger.info(f"Generating selectors with LLM for {url}")
        selectors = await selector_generator.create_full_extraction_config(url, html, extraction_spec)

        if selectors:
            # Replace the extract section with LLM-generated selectors
            config["extract"] = selectors
            logger.info(f"Enhanced configuration with LLM-generated selectors")
        else:
            logger.warning("LLM failed to generate selectors, keeping template selectors")

        return config

    async def validate_selectors(self, url: str, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Test selectors against the actual page and report results.

        Args:
            url: URL of the page
            config: Configuration with selectors

        Returns:
            Dict: Dictionary of test results for each selector
        """
        # Initialize scraper
        test_config = {
            "url": url,
            "render_js": config.get("render_js", True)
        }

        try:
            async with Crawl4AIScraper(test_config) as scraper:
                # Load the page
                html = await scraper.navigate_to(url)
                if not html:
                    logger.error(f"Failed to load URL for validation: {url}")
                    return {}

                # Initialize validation results
                validation_results = {}

                # Test each selector
                for key, selector in config.get("extract", {}).items():
                    if selector.get("type") == "group":
                        # For group selectors, test the container and each field
                        container_selector = selector.get("container", "")
                        soup = BeautifulSoup(html, 'html.parser')
                        containers = soup.select(container_selector)

                        if containers:
                            validation_results[key] = {
                                "container": True,
                                "container_count": len(containers),
                                "fields": {}
                            }

                            # Test each field within a sample container
                            for field_name, field_selector in selector.get("fields", {}).items():
                                field_query = field_selector.get("query", "")
                                field_results = containers[0].select(field_query)

                                validation_results[key]["fields"][field_name] = {
                                    "success": len(field_results) > 0,
                                    "count": len(field_results),
                                    "sample": field_results[0].get_text(strip=True) if field_results else None
                                }
                        else:
                            validation_results[key] = {
                                "container": False,
                                "container_count": 0,
                                "fields": {}
                            }
                    else:
                        # For simple selectors, test directly
                        query = selector.get("query", "")
                        soup = BeautifulSoup(html, 'html.parser')
                        results = soup.select(query)

                        validation_results[key] = {
                            "success": len(results) > 0,
                            "count": len(results),
                            "sample": results[0].get_text(strip=True) if results else None
                        }

                        # If attribute is specified, check it
                        if selector.get("attribute") and results:
                            attribute = selector.get("attribute")
                            has_attr = results[0].has_attr(attribute)
                            validation_results[key]["attribute_present"] = has_attr
                            validation_results[key]["attribute_sample"] = results[0].get(
                                attribute) if has_attr else None

                logger.info(f"Validated {len(validation_results)} selectors")
                return validation_results

        except Exception as e:
            logger.error(f"Error validating selectors: {e}")
            return {}

    async def generate_config(self, url: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a complete configuration for a URL using the hybrid approach.

        Args:
            url: URL to generate configuration for
            output_path: Optional path to save the configuration

        Returns:
            Dict: Generated configuration
        """
        logger.info(f"Generating configuration for URL: {url}")

        # Step 1: Detect site type
        site_type = await self.detect_site_type(url)

        # Step 2: Load template
        config = await self.load_template(site_type)

        # Update URL in config
        config["url"] = url

        # Step 3: Get HTML content for LLM analysis
        scraper_config = {
            "url": url,
            "render_js": config.get("render_js", True)
        }

        html = ""
        try:
            async with Crawl4AIScraper(scraper_config) as scraper:
                html = await scraper.navigate_to(url)
                if not html:
                    logger.error(f"Failed to load URL: {url}")
                    return config
        except Exception as e:
            logger.error(f"Error loading URL: {e}")
            return config

        # Step 4: Enhance with LLM
        if self.llm_api_key:
            config = await self.enhance_with_llm(url, config, html)

        # Step 5: Validate selectors
        validation_results = await self.validate_selectors(url, config)

        # Add validation results to config for reference
        config["_validation"] = validation_results

        # Save configuration if output path is specified
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(output_path, 'w') as f:
                if output_path.endswith('.json'):
                    json.dump(config, f, indent=2)
                else:
                    yaml.dump(config, f, default_flow_style=False)

            logger.info(f"Saved configuration to {output_path}")

        return config


class ConfigEditor:
    """
    UI for manual adjustment of configurations.
    Implementation depends on environment - can be CLI, web-based, or GUI.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the configuration editor.

        Args:
            config: Configuration to edit
        """
        self.config = config
        self.validation = config.pop("_validation", {})

    def terminal_ui(self) -> Dict[str, Any]:
        """
        Simple terminal-based UI for editing configuration.

        Returns:
            Dict: Edited configuration
        """
        print("\n===== Configuration Editor =====\n")
        print(f"URL: {self.config.get('url', '')}")
        print(
            f"Site Type: {os.path.basename(list(self.validation.keys())[0]).split('.')[0] if self.validation else 'Unknown'}")

        # Main menu
        while True:
            print("\nOptions:")
            print("1. View/Edit General Settings")
            print("2. View/Edit Selectors")
            print("3. View Validation Results")
            print("4. Save Configuration")
            print("5. Exit")

            choice = input("\nEnter your choice (1-5): ")

            if choice == "1":
                self._edit_general_settings()
            elif choice == "2":
                self._edit_selectors()
            elif choice == "3":
                self._view_validation()
            elif choice == "4":
                self._save_config()
            elif choice == "5":
                break
            else:
                print("Invalid choice. Please try again.")

        return self.config

    def _edit_general_settings(self):
        """Edit general configuration settings."""
        print("\n----- General Settings -----\n")

        # Display current settings
        settings = {
            "url": self.config.get("url", ""),
            "render_js": self.config.get("render_js", True),
            "stealth_mode": self.config.get("stealth_mode", False),
            "navigation_type": self.config.get("navigation_type", "single"),
            "output_format": self.config.get("output_format", "json")
        }

        for key, value in settings.items():
            print(f"{key}: {value}")

        # Edit settings
        print("\nEnter new values (or press Enter to keep current value):")

        for key, value in settings.items():
            new_value = input(f"{key} [{value}]: ")
            if new_value:
                if isinstance(value, bool):
                    self.config[key] = new_value.lower() in ("true", "yes", "y", "1")
                else:
                    self.config[key] = new_value

    def _edit_selectors(self):
        """Edit extraction selectors."""
        print("\n----- Extraction Selectors -----\n")

        # Get the list of selectors
        selectors = self.config.get("extract", {})

        if not selectors:
            print("No selectors defined.")
            return

        # Display selectors
        print("Selectors:")
        for i, (key, selector) in enumerate(selectors.items(), 1):
            if selector.get("type") == "group":
                print(f"{i}. [GROUP] {key} - Container: {selector.get('container', '')}")
                print(f"   Fields: {', '.join(selector.get('fields', {}).keys())}")
            else:
                print(f"{i}. {key} - {selector.get('query', '')}")

        # Edit menu
        while True:
            print("\nOptions:")
            print("1. Edit a selector")
            print("2. Add a new selector")
            print("3. Remove a selector")
            print("4. Back to main menu")

            choice = input("\nEnter your choice (1-4): ")

            if choice == "1":
                selector_idx = input("Enter selector number to edit: ")
                try:
                    idx = int(selector_idx) - 1
                    if 0 <= idx < len(selectors):
                        key = list(selectors.keys())[idx]
                        self._edit_single_selector(key)
                    else:
                        print("Invalid selector number.")
                except ValueError:
                    print("Please enter a valid number.")
            elif choice == "2":
                self._add_selector()
            elif choice == "3":
                selector_idx = input("Enter selector number to remove: ")
                try:
                    idx = int(selector_idx) - 1
                    if 0 <= idx < len(selectors):
                        key = list(selectors.keys())[idx]
                        del self.config["extract"][key]
                        print(f"Removed selector: {key}")
                    else:
                        print("Invalid selector number.")
                except ValueError:
                    print("Please enter a valid number.")
            elif choice == "4":
                break
            else:
                print("Invalid choice. Please try again.")

    def _edit_single_selector(self, key: str):
        """
        Edit a single selector.

        Args:
            key: Key of the selector to edit
        """
        selector = self.config["extract"][key]

        print(f"\nEditing selector: {key}")

        # Edit selector type
        selector_type = selector.get("type", "css")
        new_type = input(f"Type (css/xpath/group) [{selector_type}]: ")
        if new_type and new_type in ("css", "xpath", "group"):
            selector["type"] = new_type

        if selector["type"] == "group":
            # Edit group selector
            container = selector.get("container", "")
            new_container = input(f"Container selector [{container}]: ")
            if new_container:
                selector["container"] = new_container

            multiple = selector.get("multiple", True)
            new_multiple = input(f"Multiple (true/false) [{multiple}]: ")
            if new_multiple:
                selector["multiple"] = new_multiple.lower() in ("true", "yes", "y", "1")

            # Edit fields
            fields = selector.get("fields", {})
            print("\nFields:")
            for i, (field_key, field_selector) in enumerate(fields.items(), 1):
                print(f"{i}. {field_key}: {field_selector.get('query', '')}")

            while True:
                print("\nField options:")
                print("1. Edit a field")
                print("2. Add a new field")
                print("3. Remove a field")
                print("4. Back to selector menu")

                field_choice = input("\nEnter your choice (1-4): ")

                if field_choice == "1":
                    field_idx = input("Enter field number to edit: ")
                    try:
                        idx = int(field_idx) - 1
                        if 0 <= idx < len(fields):
                            field_key = list(fields.keys())[idx]
                            self._edit_field(key, field_key)
                        else:
                            print("Invalid field number.")
                    except ValueError:
                        print("Please enter a valid number.")
                elif field_choice == "2":
                    self._add_field(key)
                elif field_choice == "3":
                    field_idx = input("Enter field number to remove: ")
                    try:
                        idx = int(field_idx) - 1
                        if 0 <= idx < len(fields):
                            field_key = list(fields.keys())[idx]
                            del self.config["extract"][key]["fields"][field_key]
                            print(f"Removed field: {field_key}")
                        else:
                            print("Invalid field number.")
                    except ValueError:
                        print("Please enter a valid number.")
                elif field_choice == "4":
                    break
                else:
                    print("Invalid choice. Please try again.")
        else:
            # Edit simple selector
            query = selector.get("query", "")
            new_query = input(f"Query selector [{query}]: ")
            if new_query:
                selector["query"] = new_query

            multiple = selector.get("multiple", False)
            new_multiple = input(f"Multiple (true/false) [{multiple}]: ")
            if new_multiple:
                selector["multiple"] = new_multiple.lower() in ("true", "yes", "y", "1")

            attribute = selector.get("attribute", "")
            new_attribute = input(f"Attribute (e.g., 'href', 'src') [{attribute}]: ")
            if new_attribute:
                if new_attribute.lower() == "none":
                    if "attribute" in selector:
                        del selector["attribute"]
                else:
                    selector["attribute"] = new_attribute

    def _add_selector(self):
        """Add a new selector."""
        key = input("Enter selector name: ")
        if not key:
            print("Selector name cannot be empty.")
            return

        if key in self.config.get("extract", {}):
            print(f"Selector '{key}' already exists.")
            return

        selector_type = input("Type (css/xpath/group): ")
        if selector_type not in ("css", "xpath", "group"):
            print("Invalid selector type. Must be css, xpath, or group.")
            return

        if "extract" not in self.config:
            self.config["extract"] = {}

        if selector_type == "group":
            container = input("Container selector: ")
            if not container:
                print("Container selector cannot be empty.")
                return

            self.config["extract"][key] = {
                "type": "group",
                "multiple": True,
                "container": container,
                "fields": {}
            }

            # Add initial fields
            add_fields = input("Add fields now? (y/n): ")
            if add_fields.lower() in ("y", "yes"):
                while True:
                    field_key = input("Enter field name (or empty to finish): ")
                    if not field_key:
                        break

                    field_query = input("Field selector: ")
                    if field_query:
                        self.config["extract"][key]["fields"][field_key] = {
                            "type": "css",
                            "query": field_query,
                            "multiple": False
                        }

                        attribute = input("Attribute (optional): ")
                        if attribute:
                            self.config["extract"][key]["fields"][field_key]["attribute"] = attribute
        else:
            query = input("Query selector: ")
            if not query:
                print("Query selector cannot be empty.")
                return

            self.config["extract"][key] = {
                "type": selector_type,
                "query": query,
                "multiple": False
            }

            attribute = input("Attribute (optional): ")
            if attribute:
                self.config["extract"][key]["attribute"] = attribute

            multiple = input("Multiple elements? (y/n): ")
            if multiple.lower() in ("y", "yes"):
                self.config["extract"][key]["multiple"] = True

    def _add_field(self, selector_key: str):
        """
        Add a field to a group selector.

        Args:
            selector_key: Key of the group selector
        """
        field_key = input("Enter field name: ")
        if not field_key:
            print("Field name cannot be empty.")
            return

        if field_key in self.config["extract"][selector_key].get("fields", {}):
            print(f"Field '{field_key}' already exists.")
            return

        field_query = input("Field selector: ")
        if not field_query:
            print("Field selector cannot be empty.")
            return

        if "fields" not in self.config["extract"][selector_key]:
            self.config["extract"][selector_key]["fields"] = {}

        self.config["extract"][selector_key]["fields"][field_key] = {
            "type": "css",
            "query": field_query,
            "multiple": False
        }

        attribute = input("Attribute (optional): ")
        if attribute:
            self.config["extract"][selector_key]["fields"][field_key]["attribute"] = attribute

        multiple = input("Multiple elements? (y/n): ")
        if multiple.lower() in ("y", "yes"):
            self.config["extract"][selector_key]["fields"][field_key]["multiple"] = True

    def _edit_field(self, selector_key: str, field_key: str):
        """
        Edit a field in a group selector.

        Args:
            selector_key: Key of the group selector
            field_key: Key of the field to edit
        """
        field = self.config["extract"][selector_key]["fields"][field_key]

        print(f"\nEditing field: {field_key}")

        # Edit field type
        field_type = field.get("type", "css")
        new_type = input(f"Type (css/xpath) [{field_type}]: ")
        if new_type and new_type in ("css", "xpath"):
            field["type"] = new_type

        # Edit query
        query = field.get("query", "")
        new_query = input(f"Query selector [{query}]: ")
        if new_query:
            field["query"] = new_query

        # Edit multiple
        multiple = field.get("multiple", False)
        new_multiple = input(f"Multiple (true/false) [{multiple}]: ")
        if new_multiple:
            field["multiple"] = new_multiple.lower() in ("true", "yes", "y", "1")

        # Edit attribute
        attribute = field.get("attribute", "")
        new_attribute = input(f"Attribute (e.g., 'href', 'src') [{attribute}]: ")
        if new_attribute:
            if new_attribute.lower() == "none":
                if "attribute" in field:
                    del field["attribute"]
            else:
                field["attribute"] = new_attribute

    def _view_validation(self):
        """View validation results."""
        print("\n----- Validation Results -----\n")

        if not self.validation:
            print("No validation results available.")
            return

        for key, result in self.validation.items():
            if isinstance(result, dict) and "success" in result:
                status = "✅ Success" if result["success"] else "❌ Failed"
                print(f"{key}: {status}")
                print(f"  Count: {result.get('count', 0)}")
                if result.get("sample"):
                    print(f"  Sample: {result.get('sample')}")
                if "attribute_present" in result:
                    attr_status = "✅ Present" if result["attribute_present"] else "❌ Missing"
                    print(f"  Attribute: {attr_status}")
                    if result.get("attribute_sample"):
                        print(f"  Attribute Sample: {result.get('attribute_sample')}")
            elif isinstance(result, dict) and "container" in result:
                status = "✅ Success" if result["container"] else "❌ Failed"
                print(f"{key} (Group): {status}")
                print(f"  Container Count: {result.get('container_count', 0)}")

                if "fields" in result:
                    print("  Fields:")
                    for field_name, field_result in result["fields"].items():
                        field_status = "✅ Success" if field_result.get("success") else "❌ Failed"
                        print(f"    {field_name}: {field_status}")
                        print(f"      Count: {field_result.get('count', 0)}")
                        if field_result.get("sample"):
                            print(f"      Sample: {field_result.get('sample')}")
            else:
                print(f"{key}: {result}")

        input("\nPress Enter to continue...")

    def _save_config(self):
        """Save configuration to file."""
        file_path = input("Enter file path to save configuration: ")
        if not file_path:
            print("File path cannot be empty.")
            return

        try:
            output_dir = os.path.dirname(file_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(file_path, 'w') as f:
                if file_path.endswith('.json'):
                    json.dump(self.config, f, indent=2)
                else:
                    yaml.dump(self.config, f, default_flow_style=False)

            print(f"Configuration saved to {file_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Generate Crawl4AI configuration using hybrid approach")
    parser.add_argument("url", help="URL to generate configuration for")
    parser.add_argument("-o", "--output", help="Output file path for configuration")
    parser.add_argument("-k", "--key", help="API key for LLM service (Anthropic or OpenAI)")
    parser.add_argument("-p", "--provider", choices=["anthropic", "openai"], default="anthropic", help="LLM provider")
    parser.add_argument("-m", "--model", default="claude-3-haiku-20240307", help="LLM model to use")
    parser.add_argument("-e", "--edit", action="store_true", help="Open editor for manual adjustment")

    args = parser.parse_args()

    # Initialize configuration generator
    generator = ConfigGenerator(
        llm_api_key=args.key,
        llm_provider=args.provider,
        llm_model=args.model
    )

    # Generate configuration
    config = await generator.generate_config(args.url)

    # Open editor for manual adjustment if requested
    if args.edit:
        editor = ConfigEditor(config)
        config = editor.terminal_ui()

    # Save configuration if output path is specified
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(args.output, 'w') as f:
            if args.output.endswith('.json'):
                json.dump(config, f, indent=2)
            else:
                yaml.dump(config, f, default_flow_style=False)

        print(f"Configuration saved to {args.output}")
    else:
        # Print configuration to console
        print("\nGenerated Configuration:")
        print(yaml.dump(config, default_flow_style=False))


if __name__ == "__main__":
    asyncio.run(main())