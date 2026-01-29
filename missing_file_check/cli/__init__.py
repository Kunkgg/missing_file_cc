"""
Command-line interface for Missing File Check tool.

Provides convenient CLI commands for scanning, reporting, and managing tasks.
"""

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from loguru import logger

from missing_file_check.config.models import TaskConfig
from missing_file_check.scanner.checker import MissingFileChecker
from missing_file_check.storage.database import DatabaseManager
from missing_file_check.storage.models import TaskModel
from missing_file_check.storage.report_generator import ReportGenerator
from missing_file_check.storage.repository import MissingFileRepository


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
@click.option(
    "--search-version",
    multiple=True,
    help="指定搜索版本，支持传入多个值（空格分隔），默认为空（全选）",
)
@click.option(
    "--group-id",
    multiple=True,
    type=int,
    help="指定分组ID，支持传入多个值（空格分隔），默认为空（全选）",
)
@click.option(
    "--source-type",
    multiple=True,
    help="指定来源类型，支持传入多个值（空格分隔），默认为空（全选）",
)
@click.option("--output", "-o", type=click.Path(), help="报告输出路径")
@click.option("--no-parallel", is_flag=True, help="禁用并行处理")
@click.pass_context
def batch(ctx, search_version, group_id, source_type, output, no_parallel):
    """
    批量执行文件扫描任务

    示例：
        missing-file-check batch --search-version v1.0 v2.0 --source-type git
        missing-file-check batch --group-id 1 2 --output ./reports
    """
    try:
        # Initialize database connection
        db_manager = DatabaseManager()
        db_manager.initialize()
        session = db_manager.SessionLocal()
        repo = MissingFileRepository(session)

        # Build filter parameters
        search_versions = list(search_version) if search_version else None
        group_ids = list(group_id) if group_id else None
        source_types = list(source_type) if source_type else None

        logger.info("=" * 60)
        logger.info("批量任务执行")
        logger.info("=" * 60)
        logger.info(f"搜索版本: {search_versions or '全部'}")
        logger.info(f"分组ID: {group_ids or '全部'}")
        logger.info(f"来源类型: {source_types or '全部'}")

        # Query tasks from database
        tasks = repo.query_tasks(
            search_versions=search_versions,
            group_ids=group_ids,
            source_types=source_types,
            active_only=True,
        )

        if not tasks:
            logger.warning("未找到符合条件任务")
            return

        logger.info(f"找到 {len(tasks)} 个待执行任务")
        logger.info("=" * 60)

        # Execute tasks and collect results
        task_results = execute_tasks_batch(
            repo, tasks, output=output, no_parallel=no_parallel, quiet=ctx.obj["quiet"]
        )

        # Display batch summary
        display_batch_summary(task_results)

    except Exception as e:
        logger.error(f"批量执行错误：{e}")
        if ctx.obj["verbose"]:
            logger.exception("详细错误信息:")
        sys.exit(1)
    finally:
        if "session" in locals():
            session.close()


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


@dataclass
class TaskExecutionResult:
    """Result of a single task execution."""

    task_id: int
    task_name: str
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


def build_task_config_from_model(task: TaskModel, session) -> TaskConfig:
    """Build TaskConfig from TaskModel database record."""
    from missing_file_check.storage.repository import MissingFileRepository

    repo = MissingFileRepository(session)

    # Load project relations
    project_relations = repo.get_project_relations(task.id)

    # Load path prefixes
    path_prefixes = repo.get_path_prefixes(task.id)

    # Load shield rules
    shield_rules = repo.get_shield_rules(task.id, enabled_only=True)

    # Load mapping rules
    mapping_rules = repo.get_mapping_rules(task.id, enabled_only=True)

    # Build target projects from project relations
    target_projects = []
    baseline_projects = []

    for pr in project_relations:
        adapter_config = pr.get_adapter_config() or {}

        project_info = {
            "project_id": str(pr.project_id),
            "project_name": f"Project-{pr.project_id}",
            "project_type": pr.platform_type,
            "connection": adapter_config,
        }

        if pr.role == "target":
            target_projects.append(project_info)
        else:
            baseline_projects.append(project_info)

    # Build path prefixes
    prefixes = [
        {"project_id": str(p.project_id), "prefix": p.prefix} for p in path_prefixes
    ]

    # Build shield rules
    shields = [
        {
            "id": f"SHIELD-{r.id}",
            "pattern": r.pattern,
            "remark": r.remark or "",
        }
        for r in shield_rules
    ]

    # Build mapping rules
    mappings = [
        {
            "id": f"MAP-{r.id}",
            "source_pattern": r.source_pattern,
            "target_pattern": r.target_pattern,
            "remark": r.remark or "",
        }
        for r in mapping_rules
    ]

    return TaskConfig(
        task_id=f"TASK-{task.id}",
        target_projects=target_projects,
        baseline_projects=baseline_projects,
        baseline_selector_strategy=task.baseline_selector_strategy,
        baseline_selector_params=task.get_selector_params(),
        path_prefixes=prefixes,
        shield_rules=shields,
        mapping_rules=mappings,
    )


def execute_tasks_batch(
    repo: MissingFileRepository,
    tasks: List[TaskModel],
    output: Optional[str] = None,
    no_parallel: bool = False,
    quiet: bool = False,
) -> List[TaskExecutionResult]:
    """
    Execute a batch of tasks and collect results.

    Args:
        repo: Repository instance for database access
        tasks: List of TaskModel instances to execute
        output: Optional output path for reports
        no_parallel: Disable parallel processing
        quiet: Suppress non-error output

    Returns:
        List of TaskExecutionResult instances
    """
    results: List[TaskExecutionResult] = []

    for task in tasks:
        start_time = time.time()
        error_message = None
        statistics = None

        logger.info(f"执行任务 [{task.id}]...")

        try:
            # Build task config from database model
            task_config = build_task_config_from_model(task, repo.session)

            # Execute scan
            checker = MissingFileChecker(task_config, enable_parallel=not no_parallel)
            result = checker.check()

            # Save results to database
            report_url = None
            if output:
                generator = ReportGenerator()
                output_path = Path(output) / f"report_{task.id}.html"
                generator.generate_html(result, output_path)
                report_url = str(output_path)

            repo.save_task_and_results(task.id, result, report_url=report_url)

            # Collect statistics
            statistics = {
                "missed_count": result.statistics.missed_count,
                "failed_count": result.statistics.failed_count,
                "passed_count": result.statistics.passed_count,
                "shielded_count": result.statistics.shielded_count,
                "remapped_count": result.statistics.remapped_count,
                "target_file_count": result.statistics.target_file_count,
                "baseline_file_count": result.statistics.baseline_file_count,
            }

            if not quiet:
                logger.success(f"任务 [{task.id}] 完成")

        except Exception as e:
            error_message = str(e)
            logger.error(f"任务 [{task.id}] 失败: {e}")

        duration = time.time() - start_time

        results.append(
            TaskExecutionResult(
                task_id=task.id,
                task_name=f"TASK-{task.id}",
                success=error_message is None,
                duration_seconds=duration,
                error_message=error_message,
                statistics=statistics,
            )
        )

    return results


def display_batch_summary(results: List[TaskExecutionResult]):
    """
    Display batch execution summary using plain text table.

    Args:
        results: List of TaskExecutionResult instances
    """
    logger.info("=" * 60)
    logger.info("批量执行汇总")
    logger.info("=" * 60)

    total = len(results)
    success_count = sum(1 for r in results if r.success)
    failed_count = total - success_count

    logger.info(f"总执行任务数: {total}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {failed_count}")
    logger.info("=" * 60)

    # Print detailed results table
    print_results_table(results)


def print_results_table(results: List[TaskExecutionResult]):
    """
    Print results in a plain text table format.

    Args:
        results: List of TaskExecutionResult instances
    """
    # Define column headers and alignments
    headers = ["ID", "状态", "耗时", "缺失", "失败", "通过"]
    alignments = ["<", "<", ">", ">", ">", ">"]

    # Calculate column widths
    rows = []
    for r in results:
        status = "成功" if r.success else "失败"
        missed = str(r.statistics.get("missed_count", "-") if r.statistics else "-")
        failed = str(r.statistics.get("failed_count", "-") if r.statistics else "-")
        passed = str(r.statistics.get("passed_count", "-") if r.statistics else "-")
        duration = f"{r.duration_seconds:.2f}s"

        rows.append([str(r.task_id), status, duration, missed, failed, passed])

    # Print table
    print_table(headers, rows, alignments)


def print_table(
    headers: List[str],
    rows: List[List[str]],
    alignments: List[str] = None,
    padding: int = 2,
):
    """
    Print a formatted table using plain text.

    Args:
        headers: List of column headers
        rows: List of rows (each row is a list of cell values)
        alignments: List of alignments for each column ('<', '>', '^')
        padding: Number of spaces around cell content
    """
    if not rows:
        logger.info("无数据")
        return

    if alignments is None:
        alignments = ["<"] * len(headers)

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Build separator line
    separator = "+"
    for width in col_widths:
        separator += "-" * (width + 2 * padding) + "+"

    # Print table
    print()
    print(separator)
    print("|" + " " * padding, end="")
    for i, header in enumerate(headers):
        content = (
            header.ljust(col_widths[i])
            if alignments[i] == "<"
            else header.rjust(col_widths[i])
        )
        print(content + " " * padding + "|", end="")
    print()
    print(separator)

    # Print rows
    for row in rows:
        print("|" + " " * padding, end="")
        for i, cell in enumerate(row):
            cell_str = str(cell)
            if alignments[i] == "<":
                content = cell_str.ljust(col_widths[i])
            elif alignments[i] == ">":
                content = cell_str.rjust(col_widths[i])
            else:
                content = cell_str.center(col_widths[i])
            print(content + " " * padding + "|", end="")
        print()

    print(separator)
    print()


def main():
    """Entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
