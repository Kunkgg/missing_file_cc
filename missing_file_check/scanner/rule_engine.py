"""
Rule engine for applying shield and mapping rules to missing files.

Ensures rules are decoupled by processing them in a fixed order:
1. Shield rules (exclude files)
2. Mapping rules (handle renamed/relocated files)
"""

import re
from fnmatch import fnmatch
from typing import Dict, List, Optional, Set, Tuple

from missing_file_check.config.models import ShieldRule, MappingRule
from missing_file_check.adapters.base import FileEntry


class RuleEngine:
    """Applies shield and mapping rules to categorize missing files."""

    def __init__(
        self,
        shield_rules: List[ShieldRule],
        mapping_rules: List[MappingRule],
    ):
        """
        Initialize rule engine with compiled rules.

        Args:
            shield_rules: List of enabled shield rules
            mapping_rules: List of enabled mapping rules
        """
        # Compile shield rules (support both glob and regex patterns)
        self._shield_rules = shield_rules
        self._compiled_shields = []
        for rule in shield_rules:
            try:
                # Try to compile as regex first
                compiled = re.compile(rule.pattern)
                self._compiled_shields.append(("regex", compiled, rule))
            except re.error:
                # Fall back to glob pattern
                self._compiled_shields.append(("glob", rule.pattern, rule))

        # Compile mapping rules
        self._mapping_rules = mapping_rules
        self._compiled_mappings = []
        for rule in mapping_rules:
            try:
                source_regex = re.compile(rule.source_pattern)
                self._compiled_mappings.append((source_regex, rule))
            except re.error as e:
                raise ValueError(
                    f"Invalid mapping rule pattern '{rule.source_pattern}': {e}"
                )

    def apply_shield_rules(self, path: str) -> Optional[Tuple[str, str]]:
        """
        Check if path matches any shield rule.

        Args:
            path: Normalized file path

        Returns:
            Tuple of (rule_id, remark) if matched, None otherwise
        """
        for match_type, pattern, rule in self._compiled_shields:
            if match_type == "regex":
                if pattern.match(path):
                    return (rule.id, rule.remark)
            else:  # glob
                if fnmatch(path, pattern):
                    return (rule.id, rule.remark)
        return None

    def apply_mapping_rules(
        self, path: str, target_paths: Set[str]
    ) -> Optional[Tuple[str, str, str]]:
        """
        Check if path can be remapped and if target exists.

        Args:
            path: Normalized file path
            target_paths: Set of all target file paths

        Returns:
            Tuple of (mapped_path, rule_id, remark) if remapped and exists,
            None otherwise
        """
        for source_regex, rule in self._compiled_mappings:
            match = source_regex.match(path)
            if match:
                # Apply regex substitution
                try:
                    mapped_path = source_regex.sub(rule.target_pattern, path)
                    # Check if mapped path exists in target
                    if mapped_path in target_paths:
                        return (mapped_path, rule.id, rule.remark)
                except Exception:
                    # If substitution fails, skip this rule
                    continue
        return None

    def categorize_missing_files(
        self,
        missing_paths: Set[str],
        failed_files: List[Tuple[str, str]],
        baseline_files: Dict[str, Tuple[FileEntry, str]],
        target_paths: Set[str],
    ) -> List[Dict]:
        """
        Categorize missing and failed files by applying rules.

        Processing order (ensures no coupling):
        1. Shield rules - exclude files
        2. Mapping rules - handle renamed files
        3. Remaining are truly missed

        Args:
            missing_paths: Set of paths in baseline but not in target
            failed_files: List of (path, source_project) for failed files
            baseline_files: Dict mapping path to (FileEntry, source_project)
            target_paths: Set of all target file paths

        Returns:
            List of categorized missing file dictionaries with status:
            - "shielded": matched by shield rule
            - "remapped": matched by mapping rule and target exists
            - "missed": not matched by any rule
            - "failed": file exists but has failed status
        """
        results = []

        # Process missing files (baseline - target)
        for path in missing_paths:
            _, source_project = baseline_files[path]

            # 1. Check shield rules first
            shield_match = self.apply_shield_rules(path)
            if shield_match:
                rule_id, remark = shield_match
                results.append(
                    {
                        "path": path,
                        "status": "shielded",
                        "source_baseline_project": source_project,
                        "shielded_by": rule_id,
                        "shielded_remark": remark,
                        "remapped_by": None,
                        "remapped_to": None,
                    }
                )
                continue

            # 2. Check mapping rules
            mapping_match = self.apply_mapping_rules(path, target_paths)
            if mapping_match:
                mapped_path, rule_id, remark = mapping_match
                results.append(
                    {
                        "path": path,
                        "status": "remapped",
                        "source_baseline_project": source_project,
                        "shielded_by": None,
                        "shielded_remark": None,
                        "remapped_by": rule_id,
                        "remapped_to": mapped_path,
                        "remapped_remark": remark,
                    }
                )
                continue

            # 3. No rules matched - truly missed
            results.append(
                {
                    "path": path,
                    "status": "missed",
                    "source_baseline_project": source_project,
                    "shielded_by": None,
                    "shielded_remark": None,
                    "remapped_by": None,
                    "remapped_to": None,
                }
            )

        # Process failed files (exist in target but failed)
        for path, source_project in failed_files:
            results.append(
                {
                    "path": path,
                    "status": "failed",
                    "source_baseline_project": source_project,
                    "shielded_by": None,
                    "shielded_remark": None,
                    "remapped_by": None,
                    "remapped_to": None,
                }
            )

        return results
