"""
Configuration data models using Pydantic for validation.

This module defines all configuration objects used throughout the system.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectType(str, Enum):
    """Project type enumeration distinguishing target and baseline projects."""

    TARGET_PROJECT_API = "target_project_api"
    BASELINE_PROJECT_API = "baseline_project_api"
    FTP = "ftp"
    LOCAL = "local"


class ProjectConfig(BaseModel):
    """Project configuration with connection details."""

    project_id: str = Field(..., description="Unique project identifier")
    project_name: str = Field(..., description="Project display name")
    project_type: ProjectType = Field(..., description="Type of project data source")
    connection: Dict[str, Any] = Field(
        ..., description="Connection configuration (varies by project_type)"
    )

    @field_validator("connection")
    @classmethod
    def validate_connection(cls, v: Dict[str, Any], info) -> Dict[str, Any]:
        """Validate connection config based on project type."""
        project_type = info.data.get("project_type")

        if project_type in (ProjectType.TARGET_PROJECT_API, ProjectType.BASELINE_PROJECT_API):
            required = {"api_endpoint", "token", "project_key"}
            if not required.issubset(v.keys()):
                raise ValueError(f"API connection requires: {required}")

        elif project_type == ProjectType.FTP:
            required = {"host", "username", "password", "base_path"}
            if not required.issubset(v.keys()):
                raise ValueError(f"FTP connection requires: {required}")

        elif project_type == ProjectType.LOCAL:
            # Support both old and new formats
            has_old_format = "base_path" in v
            has_new_format = "build_info_file" in v and "file_list_file" in v

            if not (has_old_format or has_new_format):
                raise ValueError(
                    "Local connection requires either: {'base_path'} (old format) "
                    "or {'build_info_file', 'file_list_file'} (new format)"
                )

        return v


class ShieldRule(BaseModel):
    """Shield rule for excluding files from missing file detection."""

    id: str = Field(..., description="Unique rule identifier")
    pattern: str = Field(..., description="Path pattern (regex/glob)")
    remark: str = Field(default="", description="Rule description or reason")

    # Note: No 'enabled' field - disabled rules are filtered during config loading


class MappingRule(BaseModel):
    """Path mapping rule for handling renamed or relocated files."""

    id: str = Field(..., description="Unique rule identifier")
    source_pattern: str = Field(..., description="Source path pattern")
    target_pattern: str = Field(..., description="Target path pattern")
    remark: str = Field(default="", description="Rule description or reason")

    # Note: No 'enabled' field - disabled rules are filtered during config loading


class PathPrefixConfig(BaseModel):
    """Path prefix configuration for normalizing absolute paths to relative paths."""

    project_id: str = Field(..., description="Project this prefix applies to")
    prefix: str = Field(..., description="Path prefix to strip")


class TaskConfig(BaseModel):
    """Root configuration object for a scanning task."""

    task_id: str = Field(..., description="Unique task identifier")
    target_projects: List[ProjectConfig] = Field(
        ..., description="List of target projects to check"
    )
    baseline_projects: List[ProjectConfig] = Field(
        ..., description="List of baseline projects for comparison"
    )
    baseline_selector_strategy: str = Field(
        default="latest_success",
        description="Strategy name for selecting baseline projects",
    )
    baseline_selector_params: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional parameters for baseline selector strategy"
    )
    shield_rules: List[ShieldRule] = Field(
        default_factory=list, description="Shield rules (only enabled rules loaded)"
    )
    mapping_rules: List[MappingRule] = Field(
        default_factory=list, description="Path mapping rules (only enabled rules loaded)"
    )
    path_prefixes: List[PathPrefixConfig] = Field(
        default_factory=list, description="Path prefix configurations for normalization"
    )

    @field_validator("target_projects", "baseline_projects")
    @classmethod
    def validate_projects_not_empty(cls, v: List[ProjectConfig]) -> List[ProjectConfig]:
        """Ensure at least one project is configured."""
        if not v:
            raise ValueError("At least one project must be configured")
        return v
