"""Scan command for executing file scanning tasks."""

import sys
from pathlib import Path

import click
from loguru import logger

from missing_file_check.scanner.checker import MissingFileChecker
from missing_file_check.storage.report_generator import ReportGenerator
from missing_file_check.cli.utils.config import load_config_from_file


@click.command()
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
            from missing_file_check.cli.utils.config import load_config_from_database

            task_config = load_config_from_database(task_id)
        else:
            logger.error("错误：必须指定 --config 或 --task-id")
            sys.exit(1)

        # Display task info
        if not ctx.obj["quiet"]:
            from missing_file_check.cli.utils.display import display_task_info

            display_task_info(task_config)

        # Execute scan
        logger.info("执行扫描...")
        checker = MissingFileChecker(task_config, enable_parallel=not no_parallel)
        result = checker.check()
        logger.info("扫描完成")

        # Display results
        if not ctx.obj["quiet"]:
            from missing_file_check.cli.utils.display import display_scan_results

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
