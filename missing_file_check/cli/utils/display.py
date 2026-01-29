"""Display utilities for CLI output formatting."""

from typing import Any, Dict, List, Optional

from loguru import logger


def display_task_info(task_config):
    """Display task configuration info."""
    logger.info("任务配置:")
    logger.info(f"  任务ID: {task_config.task_id}")
    logger.info(f"  目标工程: {len(task_config.target_projects)}")
    logger.info(f"  基线工程: {len(task_config.baseline_projects)}")


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


def display_batch_summary(results: List["TaskExecutionResult"]):
    """Display batch execution summary with detailed failure information."""
    from missing_file_check.cli.commands.batch import TaskExecutionResult

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

    # Print detailed failure information
    if failed_count > 0:
        print_failure_details(results)


def print_results_table(results: List["TaskExecutionResult"]):
    """Print results in a plain text table format."""
    from missing_file_check.cli.commands.batch import TaskExecutionResult

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
    """Print a formatted table using plain text."""
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


def print_failure_details(results: List["TaskExecutionResult"]):
    """Print detailed failure information for failed tasks."""
    from missing_file_check.cli.commands.batch import TaskExecutionResult

    failed_tasks = [r for r in results if not r.success]

    if not failed_tasks:
        return

    logger.warning("=" * 60)
    logger.warning("失败任务详细清单")
    logger.warning("=" * 60)

    for i, result in enumerate(failed_tasks, 1):
        print()
        logger.error(f"[{i}] 任务 ID: {result.task_id}")
        logger.error(f"    异常类型: {result.error_type or 'Unknown'}")
        logger.error(f"    异常信息: {result.error_message or 'No error message'}")

        if result.error_traceback:
            # Print first few lines of traceback
            traceback_lines = result.error_traceback.strip().split("\n")
            # Limit traceback to 10 lines to avoid too much output
            if len(traceback_lines) > 10:
                traceback_lines = traceback_lines[:10] + ["..."]
            logger.debug(
                f"    堆栈跟踪:\n"
                + "\n".join(f"        {line}" for line in traceback_lines)
            )

    print()
    logger.warning("=" * 60)
