"""Init command for creating example configuration files."""

import json
from pathlib import Path

import click
import yaml
from loguru import logger


@click.command()
@click.argument("output", type=click.Path())
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="配置文件格式",
)
def init(output, format):
    """
    创建示例配置文件

    示例：
        missing-file-check init config.yaml
        missing-file-check init config.json --format json
    """
    try:
        output_path = Path(output)

        # Create example configuration
        example_config = create_example_config()

        if format == "yaml":
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    example_config, f, allow_unicode=True, default_flow_style=False
                )
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(example_config, f, indent=2, ensure_ascii=False)

        logger.success(f"配置文件已创建: {output_path}")
        logger.info("编辑配置文件后，使用以下命令执行扫描：")
        logger.info(f"  missing-file-check scan --config {output_path}")

    except Exception as e:
        logger.error(f"错误：{e}")
        raise SystemExit(1)


def create_example_config():
    """Create an example configuration."""
    return {
        "task_id": "TASK-EXAMPLE-001",
        "target_projects": [
            {
                "project_id": "target-1",
                "project_name": "Target Project",
                "project_type": "local",
                "connection": {
                    "build_info_file": "test_data/target_build_info.json",
                    "file_list_file": "test_data/target_files.csv",
                },
            }
        ],
        "baseline_projects": [
            {
                "project_id": "baseline-1",
                "project_name": "Baseline Project",
                "project_type": "local",
                "connection": {
                    "build_info_file": "test_data/baseline_build_info.json",
                    "file_list_file": "test_data/baseline_files.json",
                },
            }
        ],
        "baseline_selector_strategy": "latest_success",
        "shield_rules": [
            {"id": "SHIELD-001", "pattern": "docs/*", "remark": "文档文件"}
        ],
        "mapping_rules": [
            {
                "id": "MAP-001",
                "source_pattern": "old_(.*)\\.py",
                "target_pattern": "new_\\1.py",
                "remark": "文件重命名",
            }
        ],
        "path_prefixes": [
            {"project_id": "target-1", "prefix": "/project"},
            {"project_id": "baseline-1", "prefix": "/baseline"},
        ],
    }
