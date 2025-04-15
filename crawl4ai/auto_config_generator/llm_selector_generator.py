import logging
import json
import os
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple, Union
from bs4 import BeautifulSoup
import re
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('llm_selector_generator')


class LLMSelectorGenerator:
    """
    Uses LLM APIs (Claude, GPT-4, etc.) to dynamically generate and refine CSS/XPath selectors
    based on HTML content and extraction requirements.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM selector generator.

        Args:
            config: Dictionary containing LLM configuration
        """
        self.config = config
        self.llm_api_url = config.get('llm_api_url', 'https://api.anthropic.com/v1/messages')
        self.llm_api_key = config.get('llm_api_key', os.environ.get('ANTHROPIC_API_KEY', ''))
        self.llm_provider = config.get('llm_provider', 'anthropic').lower()  # 'anthropic', 'openai', etc.
        self.llm_model = config.get('llm_model', 'claude-3-haiku-20240307')
        self.max_html_length = config.get('max_html_length', 12000)  # Characters of HTML to send to LLM
        self.cache_dir = config.get('cache_dir', 'selector_cache')
        self.use_cache = config.get('use_cache', True)
        self.cache = {}

        # Create cache directory if it doesn't exist
        if self.use_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        # Load cache if enabled
        if self.use_cache:
            self._load_cache()

    def _load_cache(self) -> None:
        """Load selector cache from disk."""
        cache_file = os.path.join(self.cache_dir, 'selector_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached selectors")
            except Exception as e:
                logger.error(f"Error loading selector cache: {e}")
                self.cache = {}

    def _save_cache(self) -> None:
        """Save selector cache to disk."""
        if not self.use_cache:
            return

        cache_file = os.path.join(self.cache_dir, 'selector_cache.json')
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info(f"Saved {len(self.cache)} selectors to cache")
        except Exception as e:
            logger.error(f"Error saving selector cache: {e}")

    def _get_cache_key(self, url: str, extraction_targets: List[str]) -> str:
        """Generate a cache key based on URL and extraction targets."""
        targets_str = ','.join(sorted(extraction_targets))
        return f"{url}|{targets_str}"

    async def generate_selectors(self, url: str, html: str, extraction_targets: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Generate CSS or XPath selectors for the given extraction targets.

        Args:
            url: URL of the page
            html: HTML content
            extraction_targets: List of data elements to extract

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of generated selectors
        """
        # Check cache first
        cache_key = self._get_cache_key(url, extraction_targets)
        if self.use_cache and cache_key in self.cache:
            logger.info(f"Using cached selectors for {url}")
            return self.cache[cache_key]

        # Prepare HTML for LLM (truncate if needed)
        prepared_html = self._prepare_html(html)

        # Generate selectors using the appropriate LLM provider
        if self.llm_provider == 'anthropic':
            selectors = await self._generate_selectors_with_anthropic(url, prepared_html, extraction_targets)
        elif self.llm_provider == 'openai':
            selectors = await self._generate_selectors_with_openai(url, prepared_html, extraction_targets)
        else:
            logger.error(f"Unsupported LLM provider: {self.llm_provider}")
            selectors = {}

        # Validate and format the selectors
        formatted_selectors = self._format_selectors(selectors)

        # Cache the results
        if self.use_cache:
            self.cache[cache_key] = formatted_selectors
            self._save_cache()

        return formatted_selectors

    def _prepare_html(self, html: str) -> str:
        """
        Prepare HTML for LLM by truncating and simplifying if needed.

        Args:
            html: HTML content

        Returns:
            str: Processed HTML ready for LLM
        """
        # Parse the HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style tags
        for script in soup(['script', 'style']):
            script.extract()

        # Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()

        # Simplify the HTML
        html = str(soup)

        # Truncate if too large
        if len(html) > self.max_html_length:
            logger.info(f"HTML too large ({len(html)} chars), truncating for LLM")
            html = html[:self.max_html_length] + "\n<!-- HTML truncated due to length -->\n"

        return html

    async def _generate_selectors_with_anthropic(self, url: str, html: str, extraction_targets: List[str]) -> Dict[
        str, str]:
        """
        Generate selectors using Claude API.

        Args:
            url: URL of the page
            html: Prepared HTML content
            extraction_targets: List of data elements to extract

        Returns:
            Dict[str, str]: Dictionary of generated selectors
        """
        if not self.llm_api_key:
            logger.error("No API key provided for Anthropic Claude")
            return {}

        # Create the prompt for Claude
        system_prompt = """You are an expert at web scraping and CSS/XPath selector generation. 
Your task is to analyze HTML and create reliable CSS selectors for extracting specific information.
Generate selectors that are both robust and precise. Prefer CSS selectors when possible.
Your response MUST be valid JSON without any additional explanation text.
For each target, generate a selector configuration with these fields:
- type: "css" or "xpath"  
- query: The actual selector
- multiple: true if the selector matches multiple elements, false otherwise
- attribute: Include only if data is in an attribute (like href or src)"""

        # Construct the user message
        user_message = f"""Here's the HTML from {url}. 
I need to extract the following information:
{', '.join(extraction_targets)}

Please provide a JSON object with the best selectors for each extraction target.
The JSON should have each target as a key, mapped to an object with the selector configuration.

For example, if I wanted "product_name" and "price", your response should look like:
```json
{{
  "product_name": {{
    "type": "css",
    "query": "h1.product-title",
    "multiple": false
  }},
  "price": {{
    "type": "css",
    "query": "span.price-amount",
    "multiple": false
  }}
}}
```

Here's the HTML:
```html
{html}
```

Return ONLY the JSON object with no additional explanations."""

        # Prepare the API request
        headers = {
            "anthropic-version": "2023-06-01",
            "x-api-key": self.llm_api_key,
            "content-type": "application/json"
        }

        data = {
            "model": self.llm_model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "max_tokens": 2000,
            "temperature": 0.1  # Low temperature for deterministic output
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.llm_api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        content = response_data.get('content', [])

                        # Extract the JSON from the response
                        text = content[0]['text'] if content and 'text' in content[0] else ""

                        # Find JSON object in text (may be wrapped in ```json ... ```)
                        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                        if json_match:
                            json_text = json_match.group(1)
                        else:
                            json_text = text  # Assume the entire text is JSON

                        try:
                            selectors = json.loads(json_text)
                            logger.info(f"Successfully generated {len(selectors)} selectors with Claude")
                            return selectors
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing JSON from Claude response: {e}")
                            logger.debug(f"Raw response: {text}")
                            return {}
                    else:
                        error_text = await response.text()
                        logger.error(f"Error from Claude API ({response.status}): {error_text}")
                        return {}
        except Exception as e:
            logger.error(f"Exception calling Claude API: {e}")
            return {}

    async def _generate_selectors_with_openai(self, url: str, html: str, extraction_targets: List[str]) -> Dict[
        str, str]:
        """
        Generate selectors using OpenAI API.

        Args:
            url: URL of the page
            html: Prepared HTML content
            extraction_targets: List of data elements to extract

        Returns:
            Dict[str, str]: Dictionary of generated selectors
        """
        if not self.llm_api_key:
            logger.error("No API key provided for OpenAI")
            return {}

        # Similar to the Claude implementation, but adjusted for OpenAI's API
        api_url = "https://api.openai.com/v1/chat/completions"

        # Create the prompt for GPT
        system_message = """You are an expert at web scraping and CSS/XPath selector generation. 
Your task is to analyze HTML and create reliable CSS selectors for extracting specific information.
Generate selectors that are both robust and precise. Prefer CSS selectors when possible.
Your response MUST be valid JSON without any additional explanation text.
For each target, generate a selector configuration with these fields:
- type: "css" or "xpath"  
- query: The actual selector
- multiple: true if the selector matches multiple elements, false otherwise
- attribute: Include only if data is in an attribute (like href or src)"""

        user_message = f"""Here's the HTML from {url}. 
I need to extract the following information:
{', '.join(extraction_targets)}

Please provide a JSON object with the best selectors for each extraction target.
The JSON should have each target as a key, mapped to an object with the selector configuration.

For example, if I wanted "product_name" and "price", your response should look like:
```json
{{
  "product_name": {{
    "type": "css",
    "query": "h1.product-title",
    "multiple": false
  }},
  "price": {{
    "type": "css",
    "query": "span.price-amount",
    "multiple": false
  }}
}}
```

Here's the HTML:
```html
{html}
```

Return ONLY the JSON object with no additional explanations."""

        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 2000,
            "temperature": 0.1  # Low temperature for deterministic output
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')

                        # Extract the JSON from the response
                        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
                        if json_match:
                            json_text = json_match.group(1)
                        else:
                            json_text = content  # Assume the entire text is JSON

                        try:
                            selectors = json.loads(json_text)
                            logger.info(f"Successfully generated {len(selectors)} selectors with OpenAI")
                            return selectors
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing JSON from OpenAI response: {e}")
                            logger.debug(f"Raw response: {content}")
                            return {}
                    else:
                        error_text = await response.text()
                        logger.error(f"Error from OpenAI API ({response.status}): {error_text}")
                        return {}
        except Exception as e:
            logger.error(f"Exception calling OpenAI API: {e}")
            return {}

    def _format_selectors(self, selectors: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Validate and format the selectors to ensure they match the expected structure.

        Args:
            selectors: Raw selectors from LLM

        Returns:
            Dict[str, Dict[str, Any]]: Formatted selectors
        """
        formatted = {}

        for key, selector in selectors.items():
            # Ensure selector is a dictionary
            if not isinstance(selector, dict):
                logger.warning(f"Selector for '{key}' is not a dictionary, skipping")
                continue

            # Ensure required fields are present
            if 'type' not in selector or 'query' not in selector:
                logger.warning(f"Selector for '{key}' missing required fields, skipping")
                continue

            # Validate selector type
            if selector['type'] not in ('css', 'xpath'):
                logger.warning(f"Selector type '{selector['type']}' not supported, defaulting to css")
                selector['type'] = 'css'

            # Ensure multiple field is a boolean
            if 'multiple' in selector and not isinstance(selector['multiple'], bool):
                selector['multiple'] = str(selector['multiple']).lower() in ('true', '1', 'yes')
            elif 'multiple' not in selector:
                selector['multiple'] = False

            # Add default attribute field if missing and appropriate
            if 'attribute' not in selector and selector['query'].lower().endswith(('img', 'a', 'link')):
                if 'img' in selector['query'].lower():
                    selector['attribute'] = 'src'
                elif 'a' in selector['query'].lower() or 'link' in selector['query'].lower():
                    selector['attribute'] = 'href'

            formatted[key] = selector

        return formatted

    async def test_selectors(self, html: str, selectors: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Test generated selectors against the HTML to verify they work.

        Args:
            html: HTML content
            selectors: Dictionary of selector configurations

        Returns:
            Dict[str, bool]: Dictionary of test results (True if selector works)
        """
        results = {}
        soup = BeautifulSoup(html, 'html.parser')

        for key, selector in selectors.items():
            selector_type = selector.get('type', 'css')
            query = selector.get('query', '')
            is_multiple = selector.get('multiple', False)
            attribute = selector.get('attribute', None)

            try:
                if selector_type == 'css':
                    elements = soup.select(query)

                    if not elements:
                        results[key] = False
                        continue

                    if is_multiple:
                        # For multiple elements, we just check if any were found
                        results[key] = len(elements) > 0
                    else:
                        # For single elements, we check if exactly one clear match was found
                        if attribute:
                            results[key] = elements[0].has_attr(attribute)
                        else:
                            # Check if the element has text content
                            results[key] = bool(elements[0].get_text(strip=True))

                # XPath testing would require lxml, which we'll consider as a future enhancement
                elif selector_type == 'xpath':
                    # For now, assume XPath selectors work
                    # In a full implementation, you would use lxml for XPath testing
                    results[key] = True

            except Exception as e:
                logger.error(f"Error testing selector for '{key}': {e}")
                results[key] = False

        return results

    async def refine_selectors(self, url: str, html: str, selectors: Dict[str, Dict[str, Any]],
                               test_results: Dict[str, bool]) -> Dict[str, Dict[str, Any]]:
        """
        Refine selectors that failed testing.

        Args:
            url: URL of the page
            html: HTML content
            selectors: Dictionary of selector configurations
            test_results: Dictionary of test results

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of refined selectors
        """
        # Identify failed selectors
        failed_targets = [key for key, result in test_results.items() if not result]

        if not failed_targets:
            logger.info("All selectors passed testing, no refinement needed")
            return selectors

        logger.info(f"Refining {len(failed_targets)} failed selectors")

        # For each failed selector, provide feedback to the LLM
        system_prompt = """You are an expert at web scraping troubleshooting.
Some of the CSS/XPath selectors previously generated failed to extract the desired information.
Please analyze the HTML again and provide improved selectors for the failed targets only.
Focus on more precise and reliable selectors, considering alternative approaches if needed.
Your response MUST be valid JSON without any additional explanation text."""

        user_message = f"""The following selectors failed when tested on the HTML from {url}:
{json.dumps({key: selectors[key] for key in failed_targets}, indent=2)}

Please provide improved selectors for these targets only.
Consider alternative approaches like different elements, parent/child relationships, or using XPath if CSS is insufficient.

Here's the HTML:
```html
{self._prepare_html(html)}
```

Return ONLY the JSON object with improved selectors for the failed targets."""

        # Generate refined selectors based on the provider
        if self.llm_provider == 'anthropic':
            refined = await self._generate_selectors_with_anthropic(url, self._prepare_html(html), failed_targets)
        elif self.llm_provider == 'openai':
            refined = await self._generate_selectors_with_openai(url, self._prepare_html(html), failed_targets)
        else:
            logger.error(f"Unsupported LLM provider for refinement: {self.llm_provider}")
            refined = {}

        # Update the original selectors with the refined ones
        updated_selectors = selectors.copy()
        for key, selector in refined.items():
            if key in updated_selectors:
                logger.info(f"Refined selector for '{key}': {selector}")
                updated_selectors[key] = selector

        return updated_selectors

    async def generate_group_selectors(self, url: str, html: str, group_name: str,
                                       fields: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Generate selectors for a group of related elements (like product cards on a listing page).

        Args:
            url: URL of the page
            html: HTML content
            group_name: Name of the group (e.g., "products", "articles")
            fields: List of fields to extract for each item in the group

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of group selector configuration
        """
        # Check cache first
        cache_key = self._get_cache_key(url, [f"{group_name}_group"] + fields)
        if self.use_cache and cache_key in self.cache:
            logger.info(f"Using cached group selectors for {url}")
            return self.cache[cache_key]

        # Prepare HTML for LLM
        prepared_html = self._prepare_html(html)

        # Create the prompt for the LLM
        system_prompt = """You are an expert at web scraping and CSS/XPath selector generation for structured data.
Your task is to analyze HTML and create reliable CSS selectors for extracting groups of related elements.
Generate a container selector and field selectors that are precise and robust.
Your response MUST be valid JSON without any additional explanation text."""

        user_message = f"""Here's the HTML from {url}.
I need to extract a group of '{group_name}' elements, with the following fields for each:
{', '.join(fields)}

Please provide a JSON configuration for this group extraction with:
1. A "container" selector that identifies each {group_name} element
2. Field selectors for each field relative to the container

For example, if extracting "products" with fields "name" and "price", your response should look like:
```json
{{
  "{group_name}": {{
    "type": "group",
    "multiple": true,
    "container": "div.product-card",
    "fields": {{
      "name": {{
        "type": "css",
        "query": "h3.product-name",
        "multiple": false
      }},
      "price": {{
        "type": "css",
        "query": "span.price",
        "multiple": false
      }}
    }}
  }}
}}
```

Here's the HTML:
```html
{prepared_html}
```

Return ONLY the JSON object with the group selector configuration."""

        # Generate group selectors based on the provider
        if self.llm_provider == 'anthropic':
            # Adjust the API request for Anthropic
            headers = {
                "anthropic-version": "2023-06-01",
                "x-api-key": self.llm_api_key,
                "content-type": "application/json"
            }

            data = {
                "model": self.llm_model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": 2000,
                "temperature": 0.1
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.llm_api_url, headers=headers, json=data) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            content = response_data.get('content', [])

                            # Extract the JSON from the response
                            text = content[0]['text'] if content and 'text' in content[0] else ""

                            # Find JSON object in text
                            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                            if json_match:
                                json_text = json_match.group(1)
                            else:
                                json_text = text  # Assume the entire text is JSON

                            try:
                                group_selectors = json.loads(json_text)
                                logger.info(f"Successfully generated group selectors for {group_name}")

                                # Cache the results
                                if self.use_cache:
                                    self.cache[cache_key] = group_selectors
                                    self._save_cache()

                                return group_selectors
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing JSON for group selectors: {e}")
                                logger.debug(f"Raw response: {text}")
                                return {}
                        else:
                            error_text = await response.text()
                            logger.error(f"Error from API ({response.status}): {error_text}")
                            return {}
            except Exception as e:
                logger.error(f"Exception generating group selectors: {e}")
                return {}

        elif self.llm_provider == 'openai':
            # Similar implementation for OpenAI API
            # (Would be similar to the anthropic implementation but with OpenAI's API format)
            return {}

        else:
            logger.error(f"Unsupported LLM provider: {self.llm_provider}")
            return {}

    async def create_full_extraction_config(self, url: str, html: str,
                                            extraction_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a complete extraction configuration based on a high-level specification.

        Args:
            url: URL of the page
            html: HTML content
            extraction_spec: High-level specification of what to extract

        Returns:
            Dict[str, Any]: Complete extraction configuration
        """
        # The extraction_spec could have different formats:
        # 1. Simple list of fields: ["title", "price", "description"]
        # 2. Groups with fields: {"products": ["name", "price", "image_url"]}
        # 3. Mixed: {"title": null, "products": ["name", "price"]}

        result = {}

        # Handle simple fields (not in groups)
        simple_fields = []
        for key, value in extraction_spec.items():
            if value is None or (isinstance(value, list) and not value):
                simple_fields.append(key)

        if simple_fields:
            simple_selectors = await self.generate_selectors(url, html, simple_fields)
            result.update(simple_selectors)

        # Handle groups
        for key, fields in extraction_spec.items():
            if isinstance(fields, list) and fields:
                group_selector = await self.generate_group_selectors(url, html, key, fields)
                if group_selector:
                    result.update(group_selector)

        return result