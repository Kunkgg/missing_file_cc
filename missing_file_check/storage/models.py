"""
SQLAlchemy ORM models for database persistence.

Models correspond to the database schema for storing task configurations,
scan results, and missing file details.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TaskModel(Base):
    """Task configuration model (missing_file_tasks)."""

    __tablename__ = "missing_file_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer)
    search_version = Column(String(100))
    product = Column(String(100))
    tool = Column(String(100))
    source_type = Column(String(50))
    data_type = Column(String(50))

    # Baseline selection strategy
    baseline_selector_strategy = Column(String(100), default="latest_success")
    baseline_selector_params = Column(Text)  # JSON string

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    def get_selector_params(self) -> Optional[dict]:
        """Parse JSON params."""
        if self.baseline_selector_params:
            return json.loads(self.baseline_selector_params)
        return None

    def set_selector_params(self, params: Optional[dict]):
        """Set JSON params."""
        if params:
            self.baseline_selector_params = json.dumps(params)
        else:
            self.baseline_selector_params = None


class ProjectRelationModel(Base):
    """Project relation model (missing_file_project_relation)."""

    __tablename__ = "missing_file_project_relation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False)

    # Project role and platform
    role = Column(String(20), nullable=False)  # "target" or "baseline"
    platform_type = Column(String(50), nullable=False)  # "platform_a", "platform_b", "baseline"
    project_id = Column(Integer, nullable=False)

    # Adapter configuration
    adapter_type = Column(String(50))  # "api", "ftp", "local"
    adapter_config = Column(Text)  # JSON string

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_task_id", "task_id"),
        Index("idx_role_platform", "role", "platform_type"),
    )

    def get_adapter_config(self) -> Optional[dict]:
        """Parse JSON config."""
        if self.adapter_config:
            return json.loads(self.adapter_config)
        return None

    def set_adapter_config(self, config: Optional[dict]):
        """Set JSON config."""
        if config:
            self.adapter_config = json.dumps(config)
        else:
            self.adapter_config = None


class PathPrefixModel(Base):
    """Path prefix configuration model (missing_file_path_prefixes)."""

    __tablename__ = "missing_file_path_prefixes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False)
    project_relation_id = Column(Integer)  # Optional: link to specific project
    prefix = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (Index("idx_task_id", "task_id"),)


class ShieldRuleModel(Base):
    """Shield rule model (missing_file_shield_rules)."""

    __tablename__ = "missing_file_shield_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False)
    rule_id = Column(String(100), nullable=False)  # User-defined rule ID
    pattern = Column(String(500), nullable=False)
    remark = Column(String(500))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_task_id", "task_id"),
        Index("idx_enabled", "task_id", "enabled"),
    )


class MappingRuleModel(Base):
    """Mapping rule model (missing_file_mapping_rules)."""

    __tablename__ = "missing_file_mapping_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False)
    rule_id = Column(String(100), nullable=False)  # User-defined rule ID
    source_pattern = Column(String(500), nullable=False)
    target_pattern = Column(String(500), nullable=False)
    remark = Column(String(500))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_task_id", "task_id"),
        Index("idx_enabled", "task_id", "enabled"),
    )


class ScanResultModel(Base):
    """Scan result summary model (missing_file_scan_results)."""

    __tablename__ = "missing_file_scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False)

    # Scan status
    status = Column(String(20), nullable=False)  # "running", "completed", "failed"
    error_message = Column(Text)

    # Statistics
    # Note: missed_count and failed_count are real issues
    # passed_count (shielded + remapped) are reviewed and not issues
    missed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    shielded_count = Column(Integer, default=0)
    remapped_count = Column(Integer, default=0)
    target_file_count = Column(Integer, default=0)
    baseline_file_count = Column(Integer, default=0)
    target_project_count = Column(Integer, default=0)
    baseline_project_count = Column(Integer, default=0)

    # Project information (stored as JSON strings)
    target_project_ids = Column(Text)  # JSON array
    baseline_project_ids = Column(Text)  # JSON array

    # Report
    report_url = Column(String(500))
    report_generated_at = Column(DateTime)

    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_task_id", "task_id"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )

    def get_target_project_ids(self) -> list:
        """Parse target project IDs."""
        if self.target_project_ids:
            return json.loads(self.target_project_ids)
        return []

    def set_target_project_ids(self, ids: list):
        """Set target project IDs."""
        self.target_project_ids = json.dumps(ids)

    def get_baseline_project_ids(self) -> list:
        """Parse baseline project IDs."""
        if self.baseline_project_ids:
            return json.loads(self.baseline_project_ids)
        return []

    def set_baseline_project_ids(self, ids: list):
        """Set baseline project IDs."""
        self.baseline_project_ids = json.dumps(ids)


class MissingFileDetailModel(Base):
    """Missing file detail model (missing_file_details)."""

    __tablename__ = "missing_file_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_result_id = Column(Integer, nullable=False)

    # File information
    file_path = Column(String(1000), nullable=False)
    status = Column(String(20), nullable=False)  # "missed", "shielded", "remapped", "failed"
    source_baseline_project = Column(String(200))

    # Shield information
    shielded_by = Column(String(100))
    shielded_remark = Column(String(500))

    # Mapping information
    remapped_by = Column(String(100))
    remapped_to = Column(String(1000))
    remapped_remark = Column(String(500))

    # Analysis information (populated by analyzers)
    ownership = Column(String(200))
    miss_reason = Column(String(200))
    first_detected_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_scan_result_id", "scan_result_id"),
        Index("idx_status", "status"),
        Index("idx_file_path", "file_path", mysql_length=255),  # MySQL index length limit
    )
