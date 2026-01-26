# Quick Start Guide

## Installation

```bash
# Install dependencies
uv sync

# Run example
uv run python example_usage.py

# Run tests
uv run pytest tests/ -v
```

## Basic Usage

### 1. Create Configuration

```python
from missing_file_check.config.models import (
    TaskConfig,
    ProjectConfig,
    ProjectType,
    ShieldRule,
    MappingRule,
    PathPrefixConfig,
)

config = TaskConfig(
    task_id="TASK-001",

    # Target projects to check
    target_projects=[
        ProjectConfig(
            project_id="target-1",
            project_name="My Target Project",
            project_type=ProjectType.TARGET_PROJECT_API,
            connection={
                "api_endpoint": "https://api.example.com",
                "token": "your-token",
                "project_key": "TARGET-1"
            }
        )
    ],

    # Baseline projects for comparison
    baseline_projects=[
        ProjectConfig(
            project_id="baseline-1",
            project_name="My Baseline Project",
            project_type=ProjectType.BASELINE_PROJECT_API,
            connection={
                "api_endpoint": "https://api.example.com",
                "token": "your-token",
                "project_key": "BASELINE-1"
            }
        )
    ],

    # Baseline selection strategy
    baseline_selector_strategy="latest_success_commit_id",

    # Shield rules (exclude files)
    shield_rules=[
        ShieldRule(
            id="SHIELD-001",
            pattern="docs/*",
            remark="Documentation files"
        ),
        ShieldRule(
            id="SHIELD-002",
            pattern=r".*\.log$",
            remark="Log files"
        ),
    ],

    # Mapping rules (handle renamed files)
    mapping_rules=[
        MappingRule(
            id="MAP-001",
            source_pattern=r"old/(.+)",
            target_pattern=r"new/\1",
            remark="Directory restructure"
        ),
    ],

    # Path prefixes for normalization
    path_prefixes=[
        PathPrefixConfig(
            project_id="target-1",
            prefix="/workspace/project"
        ),
        PathPrefixConfig(
            project_id="baseline-1",
            prefix="/workspace/baseline"
        ),
    ],
)
```

### 2. Run Check

```python
from missing_file_check.scanner.checker import MissingFileChecker

# Create checker
checker = MissingFileChecker(config)

# Run check
result = checker.check()

# Access results
print(f"Task ID: {result.task_id}")
print(f"Timestamp: {result.timestamp}")
print(f"Total Missing: {result.statistics.total_missing}")
```

### 3. Process Results

```python
# Statistics
stats = result.statistics
print(f"Missed: {stats.missed_count}")
print(f"Shielded: {stats.shielded_count}")
print(f"Remapped: {stats.remapped_count}")
print(f"Failed: {stats.failed_count}")

# Iterate through missing files
for file in result.missing_files:
    print(f"\nPath: {file.path}")
    print(f"Status: {file.status}")
    print(f"Source: {file.source_baseline_project}")

    if file.status == "shielded":
        print(f"Shielded By: {file.shielded_by}")
        print(f"Reason: {file.shielded_remark}")

    elif file.status == "remapped":
        print(f"Remapped To: {file.remapped_to}")
        print(f"Rule: {file.remapped_by}")
```

## Baseline Selection Strategies

Choose the appropriate strategy for your use case:

### 1. latest_success_commit_id
Match baselines to targets by commit_id:
```python
config = TaskConfig(
    baseline_selector_strategy="latest_success_commit_id",
    # No params needed
)
```

### 2. latest_success_version
Match baselines to targets by b_version:
```python
config = TaskConfig(
    baseline_selector_strategy="latest_success_version",
)
```

### 3. specific_baseline_commit_id
Match a specific baseline to a specific target by commit_id:
```python
config = TaskConfig(
    baseline_selector_strategy="specific_baseline_commit_id",
    baseline_selector_params={
        "baseline_project_id": "baseline-1",
        "target_project_id": "target-1"
    }
)
```

### 4. specific_baseline_version
Match a specific baseline to a specific target by version:
```python
config = TaskConfig(
    baseline_selector_strategy="specific_baseline_version",
    baseline_selector_params={
        "baseline_project_id": "baseline-1",
        "target_project_id": "target-1"
    }
)
```

### 5. latest_success (default)
Use latest successful build without matching:
```python
config = TaskConfig(
    baseline_selector_strategy="latest_success",
)
```

### 6. no_restriction
No restrictions on baseline selection:
```python
config = TaskConfig(
    baseline_selector_strategy="no_restriction",
)
```

## Project Types

### TARGET_PROJECT_API / BASELINE_PROJECT_API
API-based projects:
```python
ProjectConfig(
    project_type=ProjectType.TARGET_PROJECT_API,
    connection={
        "api_endpoint": "https://api.example.com",
        "token": "your-token",
        "project_key": "PROJECT-1"
    }
)
```

### FTP
FTP-based projects:
```python
ProjectConfig(
    project_type=ProjectType.FTP,
    connection={
        "host": "ftp.example.com",
        "username": "user",
        "password": "pass",
        "base_path": "/scans"
    }
)
```

### LOCAL
Local file-based projects:
```python
ProjectConfig(
    project_type=ProjectType.LOCAL,
    connection={
        "base_path": "/path/to/files",
        "file_pattern": "*.json"  # optional
    }
)
```

## Creating Custom Adapters

To add support for new data sources:

```python
from missing_file_check.adapters.base import ProjectAdapter, ProjectScanResult
from missing_file_check.adapters.factory import AdapterFactory
from missing_file_check.config.models import ProjectType

class CustomAdapter(ProjectAdapter):
    def fetch_files(self, commit_id=None, b_version=None):
        # Your custom logic here
        # Return ProjectScanResult
        pass

# Register it
AdapterFactory.register(ProjectType.CUSTOM, CustomAdapter)
```

## Creating Custom Selectors

To add new baseline selection strategies:

```python
from missing_file_check.selectors.base import BaselineSelector
from missing_file_check.selectors.factory import BaselineSelectorFactory

class MyCustomSelector(BaselineSelector):
    def select(self, baseline_configs, target_results):
        # Your custom selection logic
        # Return List[ProjectScanResult]
        pass

# Register it
BaselineSelectorFactory.register("my_strategy", MyCustomSelector)

# Use it
config = TaskConfig(
    baseline_selector_strategy="my_strategy",
)
```

## File Statuses

The system categorizes files into 4 statuses:

| Status | Meaning | Fields |
|--------|---------|--------|
| **missed** | In baseline, not in target | `source_baseline_project` |
| **shielded** | Excluded by shield rule | `shielded_by`, `shielded_remark` |
| **remapped** | Path mapping matched | `remapped_by`, `remapped_to`, `remapped_remark` |
| **failed** | In target but failed status | `source_baseline_project` |

## Rule Patterns

### Shield Rules

Support glob and regex patterns:

```python
# Glob patterns
ShieldRule(id="S1", pattern="docs/*")           # All files in docs/
ShieldRule(id="S2", pattern="*.log")            # All .log files
ShieldRule(id="S3", pattern="test_*.py")        # Test files

# Regex patterns
ShieldRule(id="S4", pattern=r".*\.tmp$")        # Temp files
ShieldRule(id="S5", pattern=r"src/.*/test/.*")  # Nested test dirs
```

### Mapping Rules

Use regex with capture groups:

```python
# Rename pattern
MappingRule(
    id="M1",
    source_pattern=r"old_(.+)\.py",
    target_pattern=r"new_\1.py"
)
# old_file.py → new_file.py

# Directory change
MappingRule(
    id="M2",
    source_pattern=r"src/(.+)",
    target_pattern=r"lib/\1"
)
# src/module.py → lib/module.py

# Complex transformation
MappingRule(
    id="M3",
    source_pattern=r"(.+)/tests/test_(.+)\.py",
    target_pattern=r"\1/test/\2_test.py"
)
# app/tests/test_main.py → app/test/main_test.py
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=missing_file_check

# Run specific test
uv run pytest tests/test_core_functionality.py::TestRuleEngine -v
```

### Writing Tests

```python
from missing_file_check.config.models import TaskConfig
from missing_file_check.scanner.checker import MissingFileChecker

def test_my_scenario():
    # Create config
    config = TaskConfig(...)

    # Create checker
    checker = MissingFileChecker(config)

    # Run check
    result = checker.check()

    # Assert results
    assert result.statistics.total_missing == expected_count
```

## Common Patterns

### Multiple Target Projects

```python
config = TaskConfig(
    target_projects=[
        ProjectConfig(...),  # Project 1
        ProjectConfig(...),  # Project 2
        ProjectConfig(...),  # Project 3
    ],
    # File lists will be merged (union)
)
```

### Multiple Baseline Projects

```python
config = TaskConfig(
    baseline_projects=[
        ProjectConfig(...),  # Baseline 1
        ProjectConfig(...),  # Baseline 2
    ],
    # File lists will be merged (union)
    # Source tracked for each file
)
```

### Complex Rules

```python
config = TaskConfig(
    shield_rules=[
        # Exclude all test files
        ShieldRule(id="S1", pattern="*/test/*"),
        # Exclude generated files
        ShieldRule(id="S2", pattern=r".*_pb2\.py$"),
        # Exclude vendor code
        ShieldRule(id="S3", pattern="vendor/*"),
    ],
    mapping_rules=[
        # Handle module reorganization
        MappingRule(
            id="M1",
            source_pattern=r"old_package/(.+)",
            target_pattern=r"new_package/\1"
        ),
        # Handle file renames
        MappingRule(
            id="M2",
            source_pattern=r"(.+)_v1\.py",
            target_pattern=r"\1_v2.py"
        ),
    ]
)
```

## Troubleshooting

### ValidationError on Configuration

Ensure all required fields are present and connection configs match project type.

### No Baseline Projects Found

Check your baseline selection strategy and ensure baselines have matching commit_id/version.

### Rules Not Matching

- Test patterns with simple strings first
- Remember paths are normalized (no leading slash)
- Use raw strings for regex: `r"pattern"`

### Performance Issues

- Use specific baseline strategies to reduce data fetching
- Consider adding more shield rules to filter early
- Profile with `cProfile` for large datasets

## Next Steps

See `IMPLEMENTATION_SUMMARY.md` for:
- Complete architecture overview
- Implementation details
- Phase 2 roadmap

See `example_usage.py` for:
- Working demonstration
- Mock adapter example
- Complete workflow
