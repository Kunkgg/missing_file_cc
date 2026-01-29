"""
Report generator for creating HTML and JSON reports.

Generates comprehensive reports from CheckResult data.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Template

from missing_file_check.scanner.checker import CheckResult


class ReportGenerator:
    """Generator for HTML and JSON reports."""

    def __init__(self, template_path: Optional[Path] = None):
        """
        Initialize report generator.

        Args:
            template_path: Optional path to custom HTML template
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

    def generate_html(
        self, result: CheckResult, output_path: Optional[Path] = None
    ) -> str:
        """
        Generate HTML report.

        Args:
            result: CheckResult from scanner
            output_path: Optional path to save HTML file

        Returns:
            Generated HTML content
        """
        html_content = self.html_template.render(
            result=result,
            datetime=datetime,
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
    ) -> tuple:
        """
        Generate both HTML and JSON reports.

        Args:
            result: CheckResult from scanner
            html_path: Optional path to save HTML file
            json_path: Optional path to save JSON file

        Returns:
            Tuple of (html_content, json_content)
        """
        html_content = self.generate_html(result, html_path)
        json_content = self.generate_json(result, json_path)

        return html_content, json_content
