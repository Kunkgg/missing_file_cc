"""
Report generator for creating HTML and JSON reports.

Generates comprehensive reports from CheckResult data.
Supports uploading detailed file lists to object storage.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Template

from missing_file_check.scanner.checker import CheckResult
from missing_file_check.storage.object_storage import (
    ObjectStorage,
    PlaceholderObjectStorage,
)


class ReportGenerator:
    """Generator for HTML and JSON reports."""

    def __init__(
        self,
        template_path: Optional[Path] = None,
        object_storage: Optional[ObjectStorage] = None,
        storage_base_url: Optional[str] = None,
    ):
        """
        Initialize report generator.

        Args:
            template_path: Optional path to custom HTML template
            object_storage: Optional object storage instance for uploading files
            storage_base_url: Base URL for download links (used if object_storage not provided)
        """
        # Try to use external template file first
        if template_path is None:
            # Default to template file in same directory
            default_template = Path(__file__).parent / "report_template.html"
            if default_template.exists():
                template_path = default_template
            else:
                raise FileNotFoundError(
                    f"Template file not found: {default_template}. "
                    "Please ensure report_template.html exists in the storage directory."
                )

        if template_path and template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                self.html_template = Template(f.read())
        else:
            raise FileNotFoundError(
                f"Template file not found: {template_path}. "
                "Please provide a valid template path."
            )

        # Initialize object storage
        self.object_storage = object_storage or PlaceholderObjectStorage(
            base_url=storage_base_url or "https://storage.example.com"
        )

        # Temporary directory for storing detail files
        self.temp_dir = Path(tempfile.mkdtemp(prefix="report_"))

    def __del__(self):
        """Cleanup temporary directory."""
        import shutil

        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_detail_file(
        self, result: CheckResult, status: str
    ) -> tuple[Path, list[dict]]:
        """
        Create detail file for a specific status type.

        Args:
            result: CheckResult from scanner
            status: File status to filter by

        Returns:
            Tuple of (file_path, file_data_list)
        """
        # Filter files by status
        files = [f for f in result.missing_files if f.status == status]

        # Convert to serializable format
        file_data = [
            {
                "path": file.path,
                "status": file.status,
                "source_baseline_project": file.source_baseline_project,
                "shielded_by": file.shielded_by,
                "shielded_remark": file.shielded_remark,
                "remapped_by": file.remapped_by,
                "remapped_to": file.remapped_to,
                "remapped_remark": file.remapped_remark,
                "ownership": file.ownership,
                "miss_reason": file.miss_reason,
                "first_detected_at": file.first_detected_at.isoformat()
                if file.first_detected_at
                else None,
            }
            for file in files
        ]

        # Create file path
        file_path = self.temp_dir / f"{result.task_id}_{status}_detail.json"

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "task_id": result.task_id,
                    "status": status,
                    "count": len(files),
                    "generated_at": datetime.now().isoformat(),
                    "files": file_data,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        return file_path, files

    def _upload_detail_file(self, local_path: Path, task_id: str, status: str) -> str:
        """
        Upload detail file to object storage.

        Args:
            local_path: Local file path
            task_id: Task identifier
            status: File status

        Returns:
            Download URL
        """
        remote_path = f"reports/{task_id}/{status}_detail.json"
        try:
            download_url = self.object_storage.upload_file(
                local_path, remote_path, content_type="application/json"
            )
            return download_url
        except Exception as e:
            print(f"[ReportGenerator] Failed to upload {status} detail file: {e}")
            # Return a placeholder URL that indicates the file was not uploaded
            return f"#download-failed-{status}"

    def _generate_download_links(self, result: CheckResult) -> dict[str, str]:
        """
        Generate download links for each status type.

        Args:
            result: CheckResult from scanner

        Returns:
            Dictionary mapping status to download URL
        """
        download_links = {}

        # Status types that need detail files
        status_types = ["missed", "failed", "shielded", "remapped"]

        for status in status_types:
            file_path, files = self._create_detail_file(result, status)

            if files:  # Only upload if there are files
                download_links[status] = self._upload_detail_file(
                    file_path, result.task_id, status
                )
            else:
                download_links[status] = None

        return download_links

    def generate_html(
        self,
        result: CheckResult,
        output_path: Optional[Path] = None,
        upload_to_storage: bool = False,
    ) -> str:
        """
        Generate HTML report.

        Args:
            result: CheckResult from scanner
            output_path: Optional path to save HTML file
            upload_to_storage: If True, upload detail files to object storage

        Returns:
            Generated HTML content
        """
        # Generate download links if needed
        download_links = None
        if upload_to_storage:
            download_links = self._generate_download_links(result)

        html_content = self.html_template.render(
            result=result,
            datetime=datetime,
            download_links=download_links,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        return html_content

    def generate_json(
        self, result: CheckResult, output_path: Optional[Path] = None
    ) -> str:
        """
        Generate JSON report.

        Args:
            result: CheckResult from scanner
            output_path: Optional path to save JSON file

        Returns:
            Generated JSON content
        """
        # Convert CheckResult to JSON-serializable dict
        report_data = {
            "task_id": result.task_id,
            "timestamp": result.timestamp.isoformat(),
            "statistics": {
                "missed_count": result.statistics.missed_count,
                "failed_count": result.statistics.failed_count,
                "passed_count": result.statistics.passed_count,
                "shielded_count": result.statistics.shielded_count,
                "remapped_count": result.statistics.remapped_count,
                "target_file_count": result.statistics.target_file_count,
                "baseline_file_count": result.statistics.baseline_file_count,
                "target_project_count": result.statistics.target_project_count,
                "baseline_project_count": result.statistics.baseline_project_count,
            },
            "target_projects": result.target_project_ids,
            "baseline_projects": result.baseline_project_ids,
            "missing_files": [
                {
                    "path": file.path,
                    "status": file.status,
                    "source_baseline_project": file.source_baseline_project,
                    "shielded_by": file.shielded_by,
                    "shielded_remark": file.shielded_remark,
                    "remapped_by": file.remapped_by,
                    "remapped_to": file.remapped_to,
                    "remapped_remark": file.remapped_remark,
                    "ownership": file.ownership,
                    "miss_reason": file.miss_reason,
                    "first_detected_at": file.first_detected_at.isoformat()
                    if file.first_detected_at
                    else None,
                }
                for file in result.missing_files
            ],
        }

        json_content = json.dumps(report_data, ensure_ascii=False, indent=2)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_content)

        return json_content

    def generate_both(
        self,
        result: CheckResult,
        html_path: Optional[Path] = None,
        json_path: Optional[Path] = None,
        upload_to_storage: bool = False,
    ) -> tuple:
        """
        Generate both HTML and JSON reports.

        Args:
            result: CheckResult from scanner
            html_path: Optional path to save HTML file
            json_path: Optional path to save JSON file
            upload_to_storage: If True, upload detail files to object storage

        Returns:
            Tuple of (html_content, json_content)
        """
        html_content = self.generate_html(
            result, html_path, upload_to_storage=upload_to_storage
        )
        json_content = self.generate_json(result, json_path)

        return html_content, json_content
