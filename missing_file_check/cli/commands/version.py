"""Version command for displaying tool information."""

import json
import sys

import click
from loguru import logger


@click.command()
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
        print(json.dumps(version_info, indent=2))
    else:
        logger.info(f"Missing File Check v{version_info['version']}")
        logger.info(f"Python {version_info['python']} on {version_info['platform']}")
