"""
Command-line interface for Missing File Check tool.

Provides convenient CLI commands for scanning, reporting, and managing tasks.
"""

import sys

import click
from loguru import logger

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


# Import commands
from missing_file_check.cli.commands import scan, batch, init, validate, version

# Add commands to CLI group
cli.add_command(scan, "scan")
cli.add_command(batch, "batch")
cli.add_command(init, "init")
cli.add_command(validate, "validate")
cli.add_command(version, "version")


def main():
    """Entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
