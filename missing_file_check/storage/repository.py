"""
Repository layer for database operations.

Provides high-level data access methods for task configuration,
scan results, and missing file details.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from missing_file_check.storage.models import (
    TaskModel,
    ProjectRelationModel,
    PathPrefixModel,
    ShieldRuleModel,
    MappingRuleModel,
    ScanResultModel,
    MissingFileDetailModel,
)
from missing_file_check.scanner.checker import CheckResult, MissingFile


class MissingFileRepository:
    """Repository for missing file check operations."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def save_scan_result(
        self, task_id: int, result: CheckResult, report_url: Optional[str] = None
    ) -> ScanResultModel:
        """
        Save scan result summary.

        Args:
            task_id: Task ID
            result: CheckResult from scanner
            report_url: Optional report URL from object storage

        Returns:
            Created ScanResultModel instance
        """
        scan_result = ScanResultModel(
            task_id=task_id,
            status="completed",
            missed_count=result.statistics.missed_count,
            failed_count=result.statistics.failed_count,
            passed_count=result.statistics.passed_count,
            shielded_count=result.statistics.shielded_count,
            remapped_count=result.statistics.remapped_count,
            target_file_count=result.statistics.target_file_count,
            baseline_file_count=result.statistics.baseline_file_count,
            target_project_count=result.statistics.target_project_count,
            baseline_project_count=result.statistics.baseline_project_count,
            report_url=report_url,
            report_generated_at=datetime.now() if report_url else None,
            started_at=result.timestamp,
            completed_at=datetime.now(),
        )

        # Set project IDs
        scan_result.set_target_project_ids(result.target_project_ids)
        scan_result.set_baseline_project_ids(result.baseline_project_ids)

        self.session.add(scan_result)
        self.session.flush()  # Get ID without committing

        return scan_result

    def save_missing_files(
        self, scan_result_id: int, missing_files: List[MissingFile]
    ) -> int:
        """
        Save missing file details in bulk.

        Args:
            scan_result_id: Scan result ID
            missing_files: List of MissingFile objects

        Returns:
            Number of records inserted
        """
        details = []
        for file in missing_files:
            detail = MissingFileDetailModel(
                scan_result_id=scan_result_id,
                file_path=file.path,
                status=file.status,
                source_baseline_project=file.source_baseline_project,
                shielded_by=file.shielded_by,
                shielded_remark=file.shielded_remark,
                remapped_by=file.remapped_by,
                remapped_to=file.remapped_to,
                remapped_remark=file.remapped_remark,
                ownership=file.ownership,
                miss_reason=file.miss_reason,
                first_detected_at=file.first_detected_at,
            )
            details.append(detail)

        # Bulk insert
        if details:
            self.session.bulk_save_objects(details)

        return len(details)

    def save_task_and_results(
        self,
        task_id: int,
        result: CheckResult,
        report_url: Optional[str] = None,
        commit: bool = True,
    ) -> ScanResultModel:
        """
        Save complete scan results (summary + details).

        Args:
            task_id: Task ID
            result: CheckResult from scanner
            report_url: Optional report URL
            commit: Whether to commit transaction

        Returns:
            Created ScanResultModel instance
        """
        # Save summary
        scan_result = self.save_scan_result(task_id, result, report_url)

        # Save details
        self.save_missing_files(scan_result.id, result.missing_files)

        if commit:
            self.session.commit()

        return scan_result

    def query_history(
        self,
        file_path: str,
        task_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[MissingFileDetailModel]:
        """
        Query historical records for a file path.

        Args:
            file_path: File path to query
            task_id: Optional task ID filter
            limit: Maximum number of records to return

        Returns:
            List of historical MissingFileDetailModel records,
            ordered by created_at descending (newest first)
        """
        query = self.session.query(MissingFileDetailModel).filter(
            MissingFileDetailModel.file_path == file_path
        )

        if task_id:
            # Join with scan_result to filter by task_id
            query = query.join(ScanResultModel).filter(
                ScanResultModel.task_id == task_id
            )

        query = query.order_by(MissingFileDetailModel.created_at.desc()).limit(limit)

        return query.all()

    def get_first_detected_at(
        self, file_path: str, task_id: Optional[int] = None
    ) -> Optional[datetime]:
        """
        Get the first detection timestamp for a file.

        Args:
            file_path: File path to query
            task_id: Optional task ID filter

        Returns:
            First detection datetime, or None if not found
        """
        query = self.session.query(MissingFileDetailModel.created_at).filter(
            MissingFileDetailModel.file_path == file_path
        )

        if task_id:
            query = query.join(ScanResultModel).filter(
                ScanResultModel.task_id == task_id
            )

        result = query.order_by(MissingFileDetailModel.created_at.asc()).first()

        return result[0] if result else None

    def get_task_config(self, task_id: int) -> Optional[TaskModel]:
        """
        Get task configuration by ID.

        Args:
            task_id: Task ID

        Returns:
            TaskModel instance or None if not found
        """
        return self.session.query(TaskModel).filter(TaskModel.id == task_id).first()

    def get_project_relations(self, task_id: int) -> List[ProjectRelationModel]:
        """
        Get all project relations for a task.

        Args:
            task_id: Task ID

        Returns:
            List of ProjectRelationModel instances
        """
        return (
            self.session.query(ProjectRelationModel)
            .filter(ProjectRelationModel.task_id == task_id)
            .all()
        )

    def get_path_prefixes(self, task_id: int) -> List[PathPrefixModel]:
        """
        Get path prefix configurations for a task.

        Args:
            task_id: Task ID

        Returns:
            List of PathPrefixModel instances
        """
        return (
            self.session.query(PathPrefixModel)
            .filter(PathPrefixModel.task_id == task_id)
            .all()
        )

    def get_shield_rules(
        self, task_id: int, enabled_only: bool = True
    ) -> List[ShieldRuleModel]:
        """
        Get shield rules for a task.

        Args:
            task_id: Task ID
            enabled_only: If True, only return enabled rules

        Returns:
            List of ShieldRuleModel instances
        """
        query = self.session.query(ShieldRuleModel).filter(
            ShieldRuleModel.task_id == task_id
        )

        if enabled_only:
            query = query.filter(ShieldRuleModel.enabled == True)

        return query.all()

    def get_mapping_rules(
        self, task_id: int, enabled_only: bool = True
    ) -> List[MappingRuleModel]:
        """
        Get mapping rules for a task.

        Args:
            task_id: Task ID
            enabled_only: If True, only return enabled rules

        Returns:
            List of MappingRuleModel instances
        """
        query = self.session.query(MappingRuleModel).filter(
            MappingRuleModel.task_id == task_id
        )

        if enabled_only:
            query = query.filter(MappingRuleModel.enabled == True)

        return query.all()

    def get_scan_results(
        self,
        task_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ScanResultModel]:
        """
        Query scan results with filters.

        Args:
            task_id: Optional task ID filter
            status: Optional status filter
            limit: Maximum number of records

        Returns:
            List of ScanResultModel instances
        """
        query = self.session.query(ScanResultModel)

        if task_id:
            query = query.filter(ScanResultModel.task_id == task_id)

        if status:
            query = query.filter(ScanResultModel.status == status)

        query = query.order_by(ScanResultModel.created_at.desc()).limit(limit)

        return query.all()

    def mark_scan_failed(self, scan_result_id: int, error_message: str):
        """
        Mark a scan result as failed.

        Args:
            scan_result_id: Scan result ID
            error_message: Error message
        """
        scan_result = (
            self.session.query(ScanResultModel)
            .filter(ScanResultModel.id == scan_result_id)
            .first()
        )

        if scan_result:
            scan_result.status = "failed"
            scan_result.error_message = error_message
            scan_result.completed_at = datetime.now()
            self.session.commit()

    def query_tasks(
        self,
        search_versions: Optional[List[str]] = None,
        group_ids: Optional[List[int]] = None,
        source_types: Optional[List[str]] = None,
        active_only: bool = True,
        limit: int = 1000,
    ) -> List[TaskModel]:
        """
        Query tasks with filters.

        Args:
            search_versions: Filter by search_version (OR relationship if multiple)
            group_ids: Filter by group_id (OR relationship if multiple)
            source_types: Filter by source_type (OR relationship if multiple)
            active_only: If True, only return active tasks
            limit: Maximum number of records to return

        Returns:
            List of TaskModel instances matching the filters
        """
        query = self.session.query(TaskModel)

        if active_only:
            query = query.filter(TaskModel.is_active == True)

        # Apply filters with OR relationship within same category
        if search_versions:
            search_filter = TaskModel.search_version.in_(search_versions)
            query = query.filter(search_filter)

        if group_ids:
            group_filter = TaskModel.group_id.in_(group_ids)
            query = query.filter(group_filter)

        if source_types:
            source_filter = TaskModel.source_type.in_(source_types)
            query = query.filter(source_filter)

        query = query.order_by(TaskModel.created_at.desc()).limit(limit)

        return query.all()
