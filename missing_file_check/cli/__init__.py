"""
Command-line interface for Missing File Check tool.

Provides convenient CLI commands for scanning, reporting, and managing tasks.
"""

import sys
from pathlib import Path
from datetime import datetime

import click
from loguru import logger

from missing_file_check.config.models import TaskConfig
from missing_file_check.scanner.checker import MissingFileChecker
from missing_file_check.storage.report_generator import ReportGenerator


# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{message}</cyan>",
    colorize=True,
)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.pass_context
def cli(ctx, verbose, quiet):
    """
    Missing File Check - 缺失文件扫描工具

    用于检测代码扫描过程中的缺失文件，确保安全扫描的完整覆盖。
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # Configure logging level
    if verbose:
        logger.remove()
        logger.add(
            sys.stderr,
            level="DEBUG",
            format="<level>{level: <8}</level> | <cyan>{message}</cyan>",
            colorize=True,
        )
    elif quiet:
        logger.remove()
        logger.add(
            sys.stderr, level="ERROR", format="<level>{message}</level>", colorize=False
        )
    else:
        logger.remove()
        logger.add(
            sys.stderr, level="INFO", format="<level>{message}</level>", colorize=False
        )


@cli.command()
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="配置文件路径 (YAML/JSON)"
)
@click.option("--task-id", "-t", help="任务ID（从数据库加载配置）")
@click.option("--output", "-o", type=click.Path(), help="报告输出路径")
@click.option("--no-parallel", is_flag=True, help="禁用并行处理")
@click.pass_context
def scan(ctx, config, task_id, output, no_parallel):
    """
    执行文件扫描任务

    示例：
        missing-file-check scan --config config.yaml --output report.html
        missing-file-check scan --task-id TASK-001
    """
    try:
        # Load configuration
        if config:
            task_config = load_config_from_file(config)
        elif task_id:
            task_config = load_config_from_database(task_id)
        else:
            logger.error("错误：必须指定 --config 或 --task-id")
            sys.exit(1)

        # Display task info
        if not ctx.obj["quiet"]:
            logger.info("任务配置:")
            logger.info(f"  任务ID: {task_config.task_id}")
            logger.info(f"  目标工程: {len(task_config.target_projects)}")
            logger.info(f"  基线工程: {len(task_config.baseline_projects)}")

        # Execute scan
        logger.info("执行扫描...")
        checker = MissingFileChecker(task_config, enable_parallel=not no_parallel)
        result = checker.check()
        logger.info("扫描完成")

        # Display results
        if not ctx.obj["quiet"]:
            display_scan_results(result)

        # Generate report if output specified
        if output:
            generator = ReportGenerator()
            output_path = Path(output)

            if output_path.suffix == ".json":
                generator.generate_json(result, output_path)
            else:
                generator.generate_html(result, output_path)

            logger.success(f"报告已生成: {output_path}")

    except Exception as e:
        logger.error(f"错误：{e}")
        if ctx.obj["verbose"]:
            logger.exception("详细错误信息:")
        sys.exit(1)


@cli.command()
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
            import yaml

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    example_config, f, allow_unicode=True, default_flow_style=False
                )
        else:
            import json

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(example_config, f, indent=2, ensure_ascii=False)

        logger.success(f"配置文件已创建: {output_path}")
        logger.info("编辑配置文件后，使用以下命令执行扫描：")
        logger.info(f"  missing-file-check scan --config {output_path}")

    except Exception as e:
        logger.error(f"错误：{e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--config", "-c", type=click.Path(exists=True), required=True, help="配置文件路径"
)
def validate(config):
    """
    验证配置文件

    示例：
        missing-file-check validate --config config.yaml
    """
    try:
        task_config = load_config_from_file(config)

        logger.success("配置文件验证通过")
        logger.info(f"任务ID: {task_config.task_id}")
        logger.info(f"目标工程: {len(task_config.target_projects)}")
        logger.info(f"基线工程: {len(task_config.baseline_projects)}")
        logger.info(f"屏蔽规则: {len(task_config.shield_rules)}")
        logger.info(f"映射规则: {len(task_config.mapping_rules)}")

    except Exception as e:
        logger.error("配置文件验证失败")
        logger.error(f"{e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"]),
    default="text",
    help="输出格式",
)
def version(format):
    """显示版本信息"""
    version_info = {
        "version": "1.0.0",
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }

    if format == "json":
        import json

        print(json.dumps(version_info, indent=2))
    else:
        logger.info(f"Missing File Check v{version_info['version']}")
        logger.info(f"Python {version_info['python']} on {version_info['platform']}")


# Helper functions


def load_config_from_file(file_path: str) -> TaskConfig:
    """Load task configuration from YAML or JSON file."""
    path = Path(file_path)

    if path.suffix in [".yaml", ".yml"]:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif path.suffix == ".json":
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    return TaskConfig(**data)


def load_config_from_database(task_id: str) -> TaskConfig:
    """Load task configuration from database."""
    # TODO: Implement database loading
    raise NotImplementedError("Database loading not yet implemented")


def display_scan_results(result):
    """Display scan results in a formatted output."""
    logger.info("=" * 40)
    logger.info("扫描统计")
    logger.info("=" * 40)
    logger.info(f"  真实缺失（需处理）: {result.statistics.missed_count}")
    logger.info(f"  扫描失败（需处理）: {result.statistics.failed_count}")
    logger.info(f"  已审核通过: {result.statistics.passed_count}")
    logger.info(f"    - 已屏蔽: {result.statistics.shielded_count}")
    logger.info(f"    - 已映射: {result.statistics.remapped_count}")
    logger.info(f"  目标文件总数: {result.statistics.target_file_count}")
    logger.info(f"  基线文件总数: {result.statistics.baseline_file_count}")
    logger.info("=" * 40)

    # Issue summary
    issues = result.statistics.missed_count + result.statistics.failed_count
    if issues > 0:
        logger.warning(f"发现 {issues} 个需要处理的问题")
    else:
        logger.success("未发现需要处理的问题")


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


def main():
    """Entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
