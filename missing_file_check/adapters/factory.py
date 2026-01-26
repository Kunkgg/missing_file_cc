"""
Adapter factory for creating appropriate adapters based on project type.

Uses registry pattern to support extensibility.
"""

from typing import Dict, Type

from missing_file_check.adapters.base import ProjectAdapter, AdapterError
from missing_file_check.config.models import ProjectConfig, ProjectType


class AdapterFactory:
    """Factory for creating project adapters based on configuration."""

    _registry: Dict[ProjectType, Type[ProjectAdapter]] = {}

    @classmethod
    def register(cls, project_type: ProjectType, adapter_class: Type[ProjectAdapter]):
        """
        Register a new adapter type.

        Args:
            project_type: ProjectType enum value
            adapter_class: Adapter class to register
        """
        cls._registry[project_type] = adapter_class

    @classmethod
    def create(cls, project_config: ProjectConfig) -> ProjectAdapter:
        """
        Create an adapter instance based on project configuration.

        Args:
            project_config: Project configuration

        Returns:
            Instantiated adapter

        Raises:
            AdapterError: If project type is not supported
        """
        adapter_class = cls._registry.get(project_config.project_type)

        if adapter_class is None:
            raise AdapterError(
                f"No adapter registered for project type: {project_config.project_type}"
            )

        return adapter_class(project_config)


# Note: Concrete adapters (API, FTP, Local) will register themselves
# when imported in Phase 2
