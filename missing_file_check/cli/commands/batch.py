"""Batch command for executing multiple file scanning tasks."""

import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from loguru import logger

from missing_file_check.scanner.checker import MissingFileChecker
from missing_file_check.storage.database import DatabaseManager
from missing_file_check.storage.models import TaskModel
from missing_file_check.storage.report_generator import ReportGenerator
from missing_file_check.storage.repository import MissingFileRepository


@dataclass
class TaskExecutionResult:
    """Result of a single task execution."""

    task_id: int
    task_name: str
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


@click.command()
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
        from missing_file_check.cli.utils.display import display_batch_summary

        display_batch_summary(task_results)

    except Exception as e:
        logger.error(f"批量执行错误：{e}")
        if ctx.obj["verbose"]:
            logger.exception("详细错误信息:")
        sys.exit(1)
    finally:
        if "session" in locals():
            session.close()


def build_task_config_from_model(task: TaskModel, session) -> "TaskConfig":
    """Build TaskConfig from TaskModel database record."""
    from missing_file_check.config.models import TaskConfig
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
    from missing_file_check.config.models import TaskConfig

    results: List[TaskExecutionResult] = []

    for task in tasks:
        start_time = time.time()
        error_message = None
        error_type = None
        error_traceback = None
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
            error_type = type(e).__name__
            error_message = str(e)
            error_traceback = traceback.format_exc()

            logger.error(f"任务 [{task.id}] 失败: [{error_type}] {error_message}")
            logger.debug(f"堆栈跟踪:\n{error_traceback}")

            # Save error result to database
            try:
                repo.save_task_error(
                    task.id, error_type, error_message, error_traceback
                )
            except Exception as db_error:
                logger.error(f"保存错误信息到数据库失败: {db_error}")

        duration = time.time() - start_time

        results.append(
            TaskExecutionResult(
                task_id=task.id,
                task_name=f"TASK-{task.id}",
                success=error_message is None,
                duration_seconds=duration,
                error_message=error_message,
                error_type=error_type,
                error_traceback=error_traceback,
                statistics=statistics,
            )
        )

    return results
