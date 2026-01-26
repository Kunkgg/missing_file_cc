"""
Database configuration loader implementation.

Loads TaskConfig from database using repository layer.
This is the interface implementation - actual platform table queries
should be implemented based on your specific schema.
"""

from typing import Dict, List

from missing_file_check.config.models import (
    TaskConfig,
    ProjectConfig,
    ProjectType,
    ShieldRule,
    MappingRule,
    PathPrefixConfig,
)
from missing_file_check.storage.database import get_session
from missing_file_check.storage.repository import MissingFileRepository


class DatabaseConfigLoader:
    """
    Loader for TaskConfig from database.

    This class provides the interface for loading configuration.
    Platform-specific table queries should be customized based on
    your actual database schema.
    """

    def load(self, task_id: int) -> TaskConfig:
        """
        Load task configuration from database.

        Args:
            task_id: Task ID

        Returns:
            Validated TaskConfig instance

        Raises:
            ValueError: If task not found or data invalid
        """
        session = get_session()
        try:
            repository = MissingFileRepository(session)

            # Load task basic info
            task = repository.get_task_config(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            if not task.is_active:
                raise ValueError(f"Task {task_id} is not active")

            # Load project relations
            relations = repository.get_project_relations(task_id)
            target_projects = self._load_target_projects(relations, session)
            baseline_projects = self._load_baseline_projects(relations, session)

            # Load rules
            shield_rules = self._load_shield_rules(repository, task_id)
            mapping_rules = self._load_mapping_rules(repository, task_id)

            # Load path prefixes
            path_prefixes = self._load_path_prefixes(repository, task_id)

            # Build TaskConfig
            return TaskConfig(
                task_id=str(task.id),
                target_projects=target_projects,
                baseline_projects=baseline_projects,
                baseline_selector_strategy=task.baseline_selector_strategy,
                baseline_selector_params=task.get_selector_params(),
                shield_rules=shield_rules,
                mapping_rules=mapping_rules,
                path_prefixes=path_prefixes,
            )

        finally:
            session.close()

    def _load_target_projects(self, relations: List, session) -> List[ProjectConfig]:
        """
        Load target project configurations.

        Args:
            relations: ProjectRelationModel list
            session: Database session

        Returns:
            List of ProjectConfig for target projects
        """
        target_projects = []

        for rel in relations:
            if rel.role != "target":
                continue

            # Query platform-specific table based on platform_type
            project_info = self._query_platform_project(
                rel.platform_type, rel.project_id, session
            )

            if not project_info:
                continue

            # Get adapter config
            adapter_config = rel.get_adapter_config() or {}

            # Map adapter_type to ProjectType enum
            project_type = self._map_adapter_type_to_project_type(
                rel.adapter_type, is_target=True
            )

            config = ProjectConfig(
                project_id=str(rel.project_id),
                project_name=project_info.get("project_name", f"Project-{rel.project_id}"),
                project_type=project_type,
                connection=adapter_config,
            )
            target_projects.append(config)

        return target_projects

    def _load_baseline_projects(self, relations: List, session) -> List[ProjectConfig]:
        """
        Load baseline project configurations.

        Args:
            relations: ProjectRelationModel list
            session: Database session

        Returns:
            List of ProjectConfig for baseline projects
        """
        baseline_projects = []

        for rel in relations:
            if rel.role != "baseline":
                continue

            # Query platform-specific table
            project_info = self._query_platform_project(
                rel.platform_type, rel.project_id, session
            )

            if not project_info:
                continue

            # Get adapter config
            adapter_config = rel.get_adapter_config() or {}

            # Map adapter_type to ProjectType enum
            project_type = self._map_adapter_type_to_project_type(
                rel.adapter_type, is_target=False
            )

            config = ProjectConfig(
                project_id=str(rel.project_id),
                project_name=project_info.get("project_name", f"Project-{rel.project_id}"),
                project_type=project_type,
                connection=adapter_config,
            )
            baseline_projects.append(config)

        return baseline_projects

    def _query_platform_project(
        self, platform_type: str, project_id: int, session
    ) -> Dict:
        """
        Query platform-specific project table.

        This is the interface that should be customized based on your schema.

        Args:
            platform_type: Platform type (platform_a, platform_b, baseline)
            project_id: Project ID in platform table
            session: Database session

        Returns:
            Dictionary with project information
        """
        # TODO: Implement actual queries based on your platform tables
        #
        # Example implementation:
        #
        # if platform_type == "platform_a":
        #     from your_models import PlatformATargetProject
        #     proj = session.query(PlatformATargetProject).filter_by(id=project_id).first()
        #     if proj:
        #         return {
        #             "project_name": proj.project_name,
        #             "c_version": proj.c_version,
        #         }
        #
        # elif platform_type == "platform_b":
        #     from your_models import PlatformBTargetProject
        #     proj = session.query(PlatformBTargetProject).filter_by(id=project_id).first()
        #     if proj:
        #         return {
        #             "project_name": proj.job_name,
        #             "branch": proj.branch,
        #         }
        #
        # elif platform_type == "baseline":
        #     from your_models import BaselineProject
        #     proj = session.query(BaselineProject).filter_by(id=project_id).first()
        #     if proj:
        #         return {
        #             "project_name": proj.project_name,
        #             "data_source": proj.data_source,
        #         }

        # Placeholder implementation - return mock data
        return {
            "project_name": f"{platform_type}_project_{project_id}",
            "platform_type": platform_type,
        }

    def _map_adapter_type_to_project_type(
        self, adapter_type: str, is_target: bool
    ) -> ProjectType:
        """
        Map adapter_type string to ProjectType enum.

        Args:
            adapter_type: Adapter type from database
            is_target: True if target project, False if baseline

        Returns:
            ProjectType enum value
        """
        adapter_type_lower = adapter_type.lower() if adapter_type else "api"

        if adapter_type_lower == "api":
            return ProjectType.TARGET_PROJECT_API if is_target else ProjectType.BASELINE_PROJECT_API
        elif adapter_type_lower == "ftp":
            return ProjectType.FTP
        elif adapter_type_lower == "local":
            return ProjectType.LOCAL
        else:
            # Default to API
            return ProjectType.TARGET_PROJECT_API if is_target else ProjectType.BASELINE_PROJECT_API

    def _load_shield_rules(
        self, repository: MissingFileRepository, task_id: int
    ) -> List[ShieldRule]:
        """Load shield rules from database."""
        rule_models = repository.get_shield_rules(task_id, enabled_only=True)
        return [
            ShieldRule(
                id=rule.rule_id,
                pattern=rule.pattern,
                remark=rule.remark or "",
            )
            for rule in rule_models
        ]

    def _load_mapping_rules(
        self, repository: MissingFileRepository, task_id: int
    ) -> List[MappingRule]:
        """Load mapping rules from database."""
        rule_models = repository.get_mapping_rules(task_id, enabled_only=True)
        return [
            MappingRule(
                id=rule.rule_id,
                source_pattern=rule.source_pattern,
                target_pattern=rule.target_pattern,
                remark=rule.remark or "",
            )
            for rule in rule_models
        ]

    def _load_path_prefixes(
        self, repository: MissingFileRepository, task_id: int
    ) -> List[PathPrefixConfig]:
        """Load path prefix configurations from database."""
        prefix_models = repository.get_path_prefixes(task_id)

        # Map project_relation_id to actual project_id
        # For now, use project_relation_id as project_id
        # You may need to join tables to get the actual project_id

        return [
            PathPrefixConfig(
                project_id=str(prefix.project_relation_id or task_id),
                prefix=prefix.prefix,
            )
            for prefix in prefix_models
        ]
