"""Validate command for checking configuration files."""

import sys

import click
from loguru import logger

from missing_file_check.cli.utils.config import load_config_from_file


@click.command()
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
