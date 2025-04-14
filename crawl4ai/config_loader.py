import yaml
import json
import os
from typing import Dict, Any, Optional, List, Union


class Crawl4AIConfigLoader:
    """
    Configuration loader for Crawl4AI-based scraper.
    Handles loading, validation, and preparation of scraping configurations.
    """

    def __init__(self, config_path: str):
        """
        Initialize the config loader with a path to a YAML or JSON configuration file.

        Args:
            config_path (str): Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        file_ext = os.path.splitext(self.config_path)[1].lower()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                if file_ext in ('.yaml', '.yml'):
                    return yaml.safe_load(file)
                elif file_ext == '.json':
                    return json.load(file)
                else:
                    raise ValueError(f"Unsupported configuration format: {file_ext}")
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ValueError(f"Error parsing configuration file: {e}")

    def _validate_config(self) -> None:
        """Validate the configuration structure and required fields."""
        required_fields = ['url']

        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Required configuration field missing: {field}")

        # Validate selectors if present
        if 'extract' in self.config:
            self._validate_selectors(self.config['extract'])

        # Validate login configuration if enabled
        if 'login' in self.config and self.config['login'].get('enabled', False):
            self._validate_login_config()

    def _validate_selectors(self, selectors: Dict[str, Any]) -> None:
        """Validate the structure of selectors configuration."""
        for key, selector in selectors.items():
            if 'type' not in selector:
                raise ValueError(f"Selector '{key}' is missing 'type' field")

            selector_type = selector['type']
            if selector_type == 'group':
                if 'fields' not in selector:
                    raise ValueError(f"Group selector '{key}' is missing 'fields'")
                if 'container' not in selector:
                    raise ValueError(f"Group selector '{key}' is missing 'container'")
                self._validate_selectors(selector['fields'])
            elif selector_type in ('css', 'xpath'):
                if 'query' not in selector:
                    raise ValueError(f"Selector '{key}' of type '{selector_type}' is missing 'query'")

    def _validate_login_config(self) -> None:
        """Validate login configuration."""
        login_config = self.config['login']

        if 'url' not in login_config:
            raise ValueError("Login configuration is missing 'url'")

        if 'actions' not in login_config:
            raise ValueError("Login configuration is missing 'actions'")

        for action in login_config['actions']:
            if 'type' not in action:
                raise ValueError("Login action is missing 'type'")
            if action['type'] in ('fill', 'click') and 'selector' not in action:
                raise ValueError(f"Login action of type '{action['type']}' is missing 'selector'")
            if action['type'] == 'fill' and 'value' not in action:
                raise ValueError("Login 'fill' action is missing 'value'")

    def get_config(self) -> Dict[str, Any]:
        """Get the loaded and validated configuration."""
        return self.config

    def get_url(self) -> str:
        """Get the target URL from configuration."""
        return self.config['url']

    def get_headers(self) -> Dict[str, str]:
        """Get request headers from configuration."""
        return self.config.get('headers', {})

    def get_login_config(self) -> Optional[Dict[str, Any]]:
        """Get login configuration if enabled."""
        login_config = self.config.get('login', {})
        return login_config if login_config.get('enabled', False) else None

    def get_pagination_config(self) -> Optional[Dict[str, Any]]:
        """Get pagination configuration if present."""
        return self.config.get('pagination')

    def get_selectors(self) -> Dict[str, Any]:
        """Get data extraction selectors."""
        return self.config.get('extract', {})

    def get_session_name(self) -> str:
        """Get session name for cookie persistence."""
        return self.config.get('session', 'default')

    def should_render_js(self) -> bool:
        """Check if JavaScript rendering is required."""
        return self.config.get('render_js', False)

    def should_extract_full_page(self) -> bool:
        """Check if the entire page should be extracted."""
        return self.config.get('full_page', False)

    def get_output_format(self) -> str:
        """Get the desired output format."""
        return self.config.get('output_format', 'json')