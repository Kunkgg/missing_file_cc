"""
Core functionality tests for the missing file checker.

Tests all Phase 1 components with mock data.
"""

import pytest
from datetime import datetime

from missing_file_check.config.models import (
    TaskConfig,
    ProjectConfig,
    ProjectType,
    ShieldRule,
    MappingRule,
    PathPrefixConfig,
)
from missing_file_check.adapters.base import BuildInfo, FileEntry, ProjectScanResult
from missing_file_check.scanner.normalizer import PathNormalizer
from missing_file_check.scanner.merger import FileMerger
from missing_file_check.scanner.comparator import FileComparator
from missing_file_check.scanner.rule_engine import RuleEngine


class TestPathNormalizer:
    """Test path normalization functionality."""

    def test_normalize_with_prefix(self):
        """Test normalizing path with configured prefix."""
        config = [PathPrefixConfig(project_id="proj1", prefix="/home/user/project")]
        normalizer = PathNormalizer(config)

        result = normalizer.normalize("/home/user/project/src/main.py", "proj1")
        assert result == "src/main.py"

    def test_normalize_without_prefix(self):
        """Test normalizing path without prefix configuration."""
        normalizer = PathNormalizer([])

        result = normalizer.normalize("/src/main.py", "proj1")
        assert result == "src/main.py"

    def test_normalize_backslashes(self):
        """Test converting backslashes to forward slashes."""
        normalizer = PathNormalizer([])

        result = normalizer.normalize("src\\windows\\path.py", "proj1")
        assert result == "src/windows/path.py"


class TestFileMerger:
    """Test file list merging functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = PathNormalizer(
            [
                PathPrefixConfig(project_id="target1", prefix="/target"),
                PathPrefixConfig(project_id="baseline1", prefix="/baseline"),
            ]
        )
        self.merger = FileMerger(self.normalizer)

    def test_merge_target_files(self):
        """Test merging multiple target project file lists."""
        results = [
            ProjectScanResult(
                project_id="target1",
                build_info=self._mock_build_info(),
                files=[
                    FileEntry("/target/src/main.py", "success"),
                    FileEntry("/target/src/utils.py", "success"),
                ],
            )
        ]

        merged = self.merger.merge_target_files(results)

        assert len(merged) == 2
        assert "src/main.py" in merged
        assert "src/utils.py" in merged

    def test_merge_baseline_files(self):
        """Test merging baseline files with source tracking."""
        results = [
            ProjectScanResult(
                project_id="baseline1",
                build_info=self._mock_build_info(),
                files=[
                    FileEntry("/baseline/src/main.py", "success"),
                    FileEntry("/baseline/src/config.py", "success"),
                ],
            )
        ]

        merged = self.merger.merge_baseline_files(results)

        assert len(merged) == 2
        assert "src/main.py" in merged
        file_entry, source = merged["src/main.py"]
        assert source == "baseline1"

    def _mock_build_info(self):
        """Create mock build info."""
        return BuildInfo(
            build_no="001",
            build_status="success",
            branch="main",
            commit_id="abc123",
            b_version="1.0.0",
            build_url="http://example.com",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )


class TestFileComparator:
    """Test file comparison functionality."""

    def test_find_missing_files(self):
        """Test identifying files in baseline but not in target."""
        baseline = {
            "src/main.py": (FileEntry("src/main.py", "success"), "baseline1"),
            "src/config.py": (FileEntry("src/config.py", "success"), "baseline1"),
            "src/utils.py": (FileEntry("src/utils.py", "success"), "baseline1"),
        }
        target = {
            "src/main.py": FileEntry("src/main.py", "success"),
        }

        missing = FileComparator.find_missing_files(baseline, target)

        assert len(missing) == 2
        assert "src/config.py" in missing
        assert "src/utils.py" in missing

    def test_find_failed_files(self):
        """Test identifying files with failed status."""
        baseline = {
            "src/main.py": (FileEntry("src/main.py", "success"), "baseline1"),
            "src/test.py": (FileEntry("src/test.py", "success"), "baseline1"),
        }
        target = {
            "src/main.py": FileEntry("src/main.py", "success"),
            "src/test.py": FileEntry("src/test.py", "failed"),
        }

        failed = FileComparator.find_failed_files(baseline, target)

        assert len(failed) == 1
        assert failed[0][0] == "src/test.py"
        assert failed[0][1] == "baseline1"


class TestRuleEngine:
    """Test rule engine functionality."""

    def test_shield_rule_with_glob(self):
        """Test shield rule with glob pattern."""
        rules = [ShieldRule(id="S1", pattern="docs/*", remark="Docs")]
        engine = RuleEngine(rules, [])

        result = engine.apply_shield_rules("docs/README.md")

        assert result is not None
        assert result[0] == "S1"
        assert result[1] == "Docs"

    def test_shield_rule_with_regex(self):
        """Test shield rule with regex pattern."""
        rules = [ShieldRule(id="S1", pattern=r".*\.log$", remark="Log files")]
        engine = RuleEngine(rules, [])

        result = engine.apply_shield_rules("app.log")

        assert result is not None
        assert result[0] == "S1"

    def test_mapping_rule(self):
        """Test path mapping rule."""
        rules = [
            MappingRule(
                id="M1",
                source_pattern=r"old/(.+)",
                target_pattern=r"new/\1",
                remark="Path migration",
            )
        ]
        engine = RuleEngine([], rules)
        target_paths = {"new/file.py"}

        result = engine.apply_mapping_rules("old/file.py", target_paths)

        assert result is not None
        assert result[0] == "new/file.py"
        assert result[1] == "M1"

    def test_categorize_missing_files(self):
        """Test complete file categorization."""
        shield_rules = [ShieldRule(id="S1", pattern="docs/*", remark="Docs")]
        mapping_rules = [
            MappingRule(
                id="M1",
                source_pattern=r"old/(.+)",
                target_pattern=r"new/\1",
                remark="Migration",
            )
        ]
        engine = RuleEngine(shield_rules, mapping_rules)

        baseline = {
            "docs/README.md": (FileEntry("docs/README.md", "success"), "baseline1"),
            "old/file.py": (FileEntry("old/file.py", "success"), "baseline1"),
            "src/missing.py": (FileEntry("src/missing.py", "success"), "baseline1"),
            "test.py": (FileEntry("test.py", "success"), "baseline1"),
        }
        target_paths = {"new/file.py", "test.py"}
        missing_paths = {"docs/README.md", "old/file.py", "src/missing.py"}
        failed_files = [("test.py", "baseline1")]

        results = engine.categorize_missing_files(
            missing_paths, failed_files, baseline, target_paths
        )

        assert len(results) == 4

        # Check statuses
        statuses = {r["path"]: r["status"] for r in results}
        assert statuses["docs/README.md"] == "shielded"
        assert statuses["old/file.py"] == "remapped"
        assert statuses["src/missing.py"] == "missed"
        assert statuses["test.py"] == "failed"


class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_config(self):
        """Test creating valid configuration."""
        config = TaskConfig(
            task_id="T1",
            target_projects=[
                ProjectConfig(
                    project_id="target1",
                    project_name="Target",
                    project_type=ProjectType.LOCAL,
                    connection={"base_path": "/path"},
                )
            ],
            baseline_projects=[
                ProjectConfig(
                    project_id="baseline1",
                    project_name="Baseline",
                    project_type=ProjectType.LOCAL,
                    connection={"base_path": "/path"},
                )
            ],
        )

        assert config.task_id == "T1"
        assert len(config.target_projects) == 1
        assert len(config.baseline_projects) == 1

    def test_api_connection_validation(self):
        """Test API connection validation."""
        with pytest.raises(ValueError, match="API connection requires"):
            ProjectConfig(
                project_id="api1",
                project_name="API Project",
                project_type=ProjectType.TARGET_PROJECT_API,
                connection={"invalid": "config"},
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
