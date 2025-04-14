import json
import csv
import os
import logging
from typing import Dict, Any, List, Union, Optional
import yaml
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('crawl4ai_output_generator')


class Crawl4AIOutputGenerator:
    """
    Output generator for Crawl4AI scraper.
    Converts scraped data to various formats and saves to files.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the output generator.

        Args:
            config: Dictionary containing output configuration
        """
        self.config = config
        self.output_format = config.get('output_format', 'json')
        self.output_dir = config.get('output_dir', 'Output')

        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_output(self, data: Union[Dict[str, Any], List[Dict[str, Any]]],
                        filename: Optional[str] = None) -> str:
        """
        Generate output file from scraped data.

        Args:
            data: Scraped data to output
            filename: Optional filename to use (otherwise auto-generated)

        Returns:
            str: Path to the generated output file
        """
        # Append timestamp if no filename provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crawl4ai_output_{timestamp}"

        # Ensure the filename has the correct extension
        if not filename.endswith(f".{self.output_format}"):
            filename = f"{filename}.{self.output_format}"

        # Full path to the output file
        output_path = os.path.join(self.output_dir, filename)

        try:
            # Process data based on the configured output format
            if self.output_format == 'json':
                self._save_as_json(data, output_path)
            elif self.output_format == 'csv':
                self._save_as_csv(data, output_path)
            elif self.output_format == 'yaml':
                self._save_as_yaml(data, output_path)
            elif self.output_format == 'markdown':
                self._save_as_markdown(data, output_path)
            else:
                # Default to JSON if format not recognized
                logger.warning(f"Unrecognized output format: {self.output_format}, using JSON instead")
                output_path = output_path.replace(f".{self.output_format}", ".json")
                self._save_as_json(data, output_path)

            logger.info(f"Output saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating output: {e}")
            # Try to save as JSON as a fallback
            fallback_path = output_path.replace(f".{self.output_format}", ".json.backup")
            try:
                self._save_as_json(data, fallback_path)
                logger.info(f"Fallback output saved to {fallback_path}")
                return fallback_path
            except Exception as e2:
                logger.error(f"Error saving fallback output: {e2}")
                return ""

    def _save_as_json(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], output_path: str) -> None:
        """
        Save data as JSON.

        Args:
            data: Data to save
            output_path: Path to the output file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_as_csv(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], output_path: str) -> None:
        """
        Save data as CSV.

        Args:
            data: Data to save
            output_path: Path to the output file
        """
        # Convert single dict to list for consistent processing
        if isinstance(data, dict):
            data = [data]

        # Handle empty data
        if not data:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["No data"])
            return

        # Flatten nested structures for CSV format
        flattened_data = []
        for item in data:
            flat_item = self._flatten_dict(item)
            flattened_data.append(flat_item)

        # Get all unique keys across all items
        all_keys = set()
        for item in flattened_data:
            all_keys.update(item.keys())

        # Sort keys for consistent output
        fieldnames = sorted(all_keys)

        # Write the CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in flattened_data:
                writer.writerow(item)

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """
        Flatten nested dictionaries for CSV output.

        Args:
            d: Dictionary to flatten
            parent_key: Key from parent dictionary
            sep: Separator for nested keys

        Returns:
            Dict[str, Any]: Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            elif isinstance(v, list):
                # For lists, convert them to a string representation
                if all(not isinstance(x, (dict, list)) for x in v):
                    items.append((new_key, ', '.join(str(x) for x in v)))
                else:
                    # For lists of complex objects, create numbered keys
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            items.extend(self._flatten_dict(item, f"{new_key}{sep}{i}", sep).items())
                        else:
                            items.append((f"{new_key}{sep}{i}", str(item)))
            else:
                items.append((new_key, v))

        return dict(items)

    def _save_as_yaml(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], output_path: str) -> None:
        """
        Save data as YAML.

        Args:
            data: Data to save
            output_path: Path to the output file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def _save_as_markdown(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], output_path: str) -> None:
        """
        Save data as Markdown.

        Args:
            data: Data to save
            output_path: Path to the output file
        """
        md_content = self._data_to_markdown(data)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

    def _data_to_markdown(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> str:
        """
        Convert data to Markdown format.

        Args:
            data: Data to convert

        Returns:
            str: Markdown representation of the data
        """
        if isinstance(data, list):
            return self._list_to_markdown(data)
        elif isinstance(data, dict):
            return self._dict_to_markdown(data)
        else:
            return str(data)

    def _dict_to_markdown(self, data: Dict[str, Any], level: int = 1) -> str:
        """
        Convert a dictionary to Markdown format.

        Args:
            data: Dictionary to convert
            level: Heading level

        Returns:
            str: Markdown representation of the dictionary
        """
        md_lines = []

        for key, value in data.items():
            if isinstance(value, dict):
                md_lines.append(f"{'#' * level} {key}\n")
                md_lines.append(self._dict_to_markdown(value, level + 1))
            elif isinstance(value, list):
                md_lines.append(f"{'#' * level} {key}\n")
                md_lines.append(self._list_to_markdown(value, level + 1))
            else:
                md_lines.append(f"**{key}**: {value}\n")

        return "\n".join(md_lines)

    def _list_to_markdown(self, data: List[Any], level: int = 1) -> str:
        """
        Convert a list to Markdown format.

        Args:
            data: List to convert
            level: Heading level

        Returns:
            str: Markdown representation of the list
        """
        md_lines = []

        for i, item in enumerate(data):
            if isinstance(item, dict):
                # For lists of dictionaries, use a heading for each item
                md_lines.append(f"{'#' * level} Item {i + 1}\n")
                md_lines.append(self._dict_to_markdown(item, level + 1))
            elif isinstance(item, list):
                md_lines.append(f"{'#' * level} Item {i + 1}\n")
                md_lines.append(self._list_to_markdown(item, level + 1))
            else:
                # For simple lists, use bullet points
                md_lines.append(f"* {item}\n")

        return "\n".join(md_lines)

    def merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple result sets into a single structure.

        Args:
            results: List of result dictionaries

        Returns:
            Dict[str, Any]: Merged results
        """
        merged = {}

        for result in results:
            for key, value in result.items():
                if key not in merged:
                    # First encounter with this key, initialize it
                    merged[key] = value
                elif isinstance(merged[key], list) and isinstance(value, list):
                    # Both are lists, extend the existing list
                    merged[key].extend(value)
                elif isinstance(merged[key], dict) and isinstance(value, dict):
                    # Both are dictionaries, merge them recursively
                    self._merge_dicts(merged[key], value)
                else:
                    # Handle conflicts by converting to a list
                    if not isinstance(merged[key], list):
                        merged[key] = [merged[key]]

                    if isinstance(value, list):
                        merged[key].extend(value)
                    else:
                        merged[key].append(value)

        return merged

    def _merge_dicts(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merge one dictionary into another.

        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target:
                if isinstance(target[key], dict) and isinstance(value, dict):
                    # Recursively merge nested dictionaries
                    self._merge_dicts(target[key], value)
                elif isinstance(target[key], list) and isinstance(value, list):
                    # Extend lists
                    target[key].extend(value)
                elif isinstance(target[key], list):
                    # Append to existing list
                    target[key].append(value)
                elif isinstance(value, list):
                    # Convert target to list and extend
                    target[key] = [target[key]] + value
                else:
                    # Handle simple value conflict by converting to a list
                    target[key] = [target[key], value]
            else:
                # Key doesn't exist in target, just copy it over
                target[key] = value