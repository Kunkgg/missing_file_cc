# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a white-box security scanning tool for detecting missing files in code scanning processes. It compares file lists between a target project and a baseline project to identify files that should have been scanned but were not, helping ensure complete security scan coverage.

The tool is designed for use in corporate white-box security infrastructure (白盒安全防护) and integrates with internal scanning platforms.

## Tech Stack

- Python 3.13+ (managed with uv)
- SQLAlchemy for ORM
- Pydantic for data validation and models
- Requests for API calls

## Development Commands

Since this project uses `uv` for package management:

```bash
# Install dependencies
uv sync

# Run the main application
uv run python main.py

# Add a new dependency
uv add <package-name>
```

## Architecture Overview

The system processes scanning tasks through a multi-stage pipeline:

### Core Workflow (per task pair)

1. **Configuration Loading**: Loads task configs from database including component info, project mappings, shield rules, path mappings, and path prefixes
2. **Target Project Data Retrieval**: Fetches latest successful scan task and file list via APIs (3 types: platform API, FTP download, local file)
3. **Baseline Project Data Retrieval**: Fetches baseline project's scan data matching the same branch/node as target project (selection logic is configurable)
4. **Comparison Logic**: Compares file lists to identify missing files:
   - Convert all paths to relative paths using path prefix configs
   - Subtract target file list from baseline file list to get initial missing files
   - Apply shield rules and path mappings to categorize files
5. **Result Output**: Generates detailed report with file status (missed/shielded/remapped) and statistics
6. **Result Re-analysis**:
   - Calls internal API to get file ownership/team info
   - Classifies miss reasons (not in list, failed status, or confirmed via cc.json logs)
   - Records first-seen timestamp for each missing file
7. **Persistence**: Saves report to object storage, stores task summary and detailed results in database

### Multi-Project Handling

For many-to-many relationships, the system executes the above workflow for each target-baseline combination and aggregates all results.

### Scale Considerations

- Baseline projects: ~60,000 files
- Target projects: up to ~200,000 files

The architecture must handle these volumes efficiently.

## Design Goals

- **Extensible rules**: New rules should be easy to add without modifying existing code
- **Clear scan flow**: The pipeline should be easy to understand and maintain
- **Decoupled rules**: Rules should not depend on each other
- **Testable**: Easy to write unit tests for individual components
- **Simple interfaces**: Avoid over-engineering

## File Status Categories

Files are classified into three states:
- `missed`: Files that exist in baseline but not in target scan
- `shielded`: Files excluded by shield configuration (includes shield_id and remark)
- `remapped`: Files with path mappings (includes remapped_to, mapping_id and remark)
