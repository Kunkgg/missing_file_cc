"""
Configuration loader for loading and validating task configurations.

Supports loading from dictionaries (for testing) and database (for production).
"""

from typing import Dict, Any

from missing_file_check.config.models import TaskConfig


class ConfigLoader:
    """Loader for task configurations with validation."""

    @staticmethod
    def load_from_dict(config_dict: Dict[str, Any]) -> TaskConfig:
        """
        Load configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary matching TaskConfig schema

        Returns:
            Validated TaskConfig instance

        Raises:
            ValidationError: If configuration is invalid
        """
        return TaskConfig.model_validate(config_dict)

    @staticmethod
    def load_from_database(task_id: int) -> TaskConfig:
        """
        Load configuration from database.

        Args:
            task_id: Task identifier (integer ID)

        Returns:
            Validated TaskConfig instance

        Raises:
            ValueError: If task not found or configuration invalid
        """
        from missing_file_check.config.database_loader import DatabaseConfigLoader

        loader = DatabaseConfigLoader()
        return loader.load(task_id)
