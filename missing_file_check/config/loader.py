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
    def load_from_database(task_id: str) -> TaskConfig:
        """
        Load configuration from database (to be implemented).

        Args:
            task_id: Task identifier

        Returns:
            Validated TaskConfig instance

        Raises:
            NotImplementedError: Database loading not yet implemented
        """
        raise NotImplementedError(
            "Database configuration loading will be implemented in Phase 2"
        )
