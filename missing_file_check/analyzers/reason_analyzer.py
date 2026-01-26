"""
Reason analyzer for classifying why files are missing.

Classifies miss reasons into categories:
- not_in_list: File not in target scan list
- failed_status: File in target but scan failed
- confirmed: Confirmed missing via cc.json logs (future)
"""

from typing import List

from missing_file_check.analyzers.base import Analyzer
from missing_file_check.scanner.checker import MissingFile


class ReasonAnalyzer(Analyzer):
    """
    Analyzer for classifying miss reasons.

    Determines why each file is missing based on its status
    and other available information.
    """

    @property
    def name(self) -> str:
        return "ReasonAnalyzer"

    def analyze(self, missing_files: List[MissingFile], context: dict) -> None:
        """
        Analyze miss reasons.

        Args:
            missing_files: List of files to analyze
            context: Analysis context
        """
        for file in missing_files:
            if not file.miss_reason:  # Don't overwrite existing reason
                file.miss_reason = self._classify_reason(file)

    def _classify_reason(self, file: MissingFile) -> str:
        """
        Classify the reason for a missing file.

        Args:
            file: MissingFile object

        Returns:
            Classified reason string
        """
        # Status-based classification
        if file.status == "failed":
            return "failed_status"
        elif file.status == "missed":
            return "not_in_list"
        elif file.status == "shielded":
            return f"shielded: {file.shielded_remark or 'by rule'}"
        elif file.status == "remapped":
            return f"remapped: {file.remapped_to}"
        else:
            return "unknown"

    def _check_cc_json_logs(self, file_path: str, context: dict) -> bool:
        """
        Check cc.json logs to confirm file presence (placeholder).

        Args:
            file_path: File path to check
            context: Analysis context

        Returns:
            True if confirmed in logs, False otherwise
        """
        # TODO: Implement cc.json log checking
        # This would involve:
        # 1. Fetch cc.json logs for the scan
        # 2. Parse JSON to find file_path
        # 3. Check if file was actually scanned
        #
        # Example:
        # cc_json = fetch_cc_json(context.get("build_no"))
        # return file_path in cc_json.get("scanned_files", [])

        return False
