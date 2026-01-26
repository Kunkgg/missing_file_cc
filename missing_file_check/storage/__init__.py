"""Storage module for persistence and report generation."""

from missing_file_check.storage.models import (
    Base,
    TaskModel,
    ProjectRelationModel,
    PathPrefixModel,
    ShieldRuleModel,
    MappingRuleModel,
    ScanResultModel,
    MissingFileDetailModel,
)
from missing_file_check.storage.database import (
    DatabaseManager,
    get_db_manager,
    init_db,
    get_session,
    session_scope,
)
from missing_file_check.storage.repository import MissingFileRepository
from missing_file_check.storage.report_generator import ReportGenerator
from missing_file_check.storage.object_storage import (
    ObjectStorage,
    ObjectStorageError,
    PlaceholderObjectStorage,
)

__all__ = [
    "Base",
    "TaskModel",
    "ProjectRelationModel",
    "PathPrefixModel",
    "ShieldRuleModel",
    "MappingRuleModel",
    "ScanResultModel",
    "MissingFileDetailModel",
    "DatabaseManager",
    "get_db_manager",
    "init_db",
    "get_session",
    "session_scope",
    "MissingFileRepository",
    "ReportGenerator",
    "ObjectStorage",
    "ObjectStorageError",
    "PlaceholderObjectStorage",
]
