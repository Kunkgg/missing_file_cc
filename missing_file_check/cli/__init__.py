"""
Command-line interface for Missing File Check tool.

Provides convenient CLI commands for scanning, reporting, and managing tasks.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from missing_file_check.config.models import TaskConfig
from missing_file_check.scanner.checker import MissingFileChecker
from missing_file_check.storage.report_generator import ReportGenerator

console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.pass_context
def cli(ctx, verbose, quiet):
    """
    Missing File Check - 缺失文件扫描工具

    用于检测代码扫描过程中的缺失文件，确保安全扫描的完整覆盖。
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet

    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    elif quiet:
        logging.basicConfig(level=logging.ERROR, format='%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), help='配置文件路径 (YAML/JSON)')
@click.option('--task-id', '-t', help='任务ID（从数据库加载配置）')
@click.option('--output', '-o', type=click.Path(), help='报告输出路径')
@click.option('--no-parallel', is_flag=True, help='禁用并行处理')
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
            console.print("[red]错误：必须指定 --config 或 --task-id[/red]")
            sys.exit(1)

        # Display task info
        if not ctx.obj['quiet']:
            console.print(Panel(
                f"[bold]任务ID:[/bold] {task_config.task_id}\n"
                f"[bold]目标工程:[/bold] {len(task_config.target_projects)}\n"
                f"[bold]基线工程:[/bold] {len(task_config.baseline_projects)}",
                title="📋 任务配置",
                border_style="blue"
            ))

        # Execute scan
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("执行扫描...", total=None)

            checker = MissingFileChecker(
                task_config,
                enable_parallel=not no_parallel
            )
            result = checker.check()

            progress.update(task, completed=True)

        # Display results
        if not ctx.obj['quiet']:
            display_scan_results(result)

        # Generate report if output specified
        if output:
            generator = ReportGenerator()
            output_path = Path(output)

            if output_path.suffix == '.json':
                generator.generate_json(result, output_path)
            else:
                generator.generate_html(result, output_path)

            console.print(f"\n[green]✓[/green] 报告已生成: {output_path}")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        if ctx.obj['verbose']:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument('output', type=click.Path())
@click.option('--format', '-f', type=click.Choice(['yaml', 'json']), default='yaml', help='配置文件格式')
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

        if format == 'yaml':
            import yaml
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(example_config, f, allow_unicode=True, default_flow_style=False)
        else:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(example_config, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓[/green] 配置文件已创建: {output_path}")
        console.print("\n编辑配置文件后，使用以下命令执行扫描：")
        console.print(f"  missing-file-check scan --config {output_path}")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='配置文件路径')
def validate(config):
    """
    验证配置文件

    示例：
        missing-file-check validate --config config.yaml
    """
    try:
        task_config = load_config_from_file(config)

        console.print("[green]✓[/green] 配置文件验证通过")
        console.print(f"\n任务ID: {task_config.task_id}")
        console.print(f"目标工程: {len(task_config.target_projects)}")
        console.print(f"基线工程: {len(task_config.baseline_projects)}")
        console.print(f"屏蔽规则: {len(task_config.shield_rules)}")
        console.print(f"映射规则: {len(task_config.mapping_rules)}")

    except Exception as e:
        console.print(f"[red]✗ 配置文件验证失败[/red]")
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text', help='输出格式')
def version(format):
    """显示版本信息"""
    version_info = {
        "version": "1.0.0",
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }

    if format == 'json':
        import json
        console.print(json.dumps(version_info, indent=2))
    else:
        console.print(f"Missing File Check v{version_info['version']}")
        console.print(f"Python {version_info['python']} on {version_info['platform']}")


# Helper functions

def load_config_from_file(file_path: str) -> TaskConfig:
    """Load task configuration from YAML or JSON file."""
    path = Path(file_path)

    if path.suffix in ['.yaml', '.yml']:
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    elif path.suffix == '.json':
        import json
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    return TaskConfig(**data)


def load_config_from_database(task_id: str) -> TaskConfig:
    """Load task configuration from database."""
    # TODO: Implement database loading
    raise NotImplementedError("Database loading not yet implemented")


def display_scan_results(result):
    """Display scan results in a formatted table."""
    # Statistics table
    stats_table = Table(title="📊 扫描统计", show_header=True, header_style="bold magenta")
    stats_table.add_column("类别", style="cyan")
    stats_table.add_column("数量", justify="right", style="green")

    stats_table.add_row("🔴 真实缺失（需处理）", str(result.statistics.missed_count))
    stats_table.add_row("❌ 扫描失败（需处理）", str(result.statistics.failed_count))
    stats_table.add_row("✅ 已审核通过", str(result.statistics.passed_count))
    stats_table.add_row("  ├─ 🛡️  已屏蔽", str(result.statistics.shielded_count))
    stats_table.add_row("  └─ 🔄 已映射", str(result.statistics.remapped_count))
    stats_table.add_row("─" * 20, "─" * 10)
    stats_table.add_row("📁 目标文件总数", str(result.statistics.target_file_count))
    stats_table.add_row("📚 基线文件总数", str(result.statistics.baseline_file_count))

    console.print(stats_table)

    # Issue summary
    issues = result.statistics.missed_count + result.statistics.failed_count
    if issues > 0:
        console.print(f"\n[yellow]⚠️  发现 {issues} 个需要处理的问题[/yellow]")
    else:
        console.print("\n[green]✓ 未发现需要处理的问题[/green]")


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
                    "file_list_file": "test_data/target_files.csv"
                }
            }
        ],
        "baseline_projects": [
            {
                "project_id": "baseline-1",
                "project_name": "Baseline Project",
                "project_type": "local",
                "connection": {
                    "build_info_file": "test_data/baseline_build_info.json",
                    "file_list_file": "test_data/baseline_files.json"
                }
            }
        ],
        "baseline_selector_strategy": "latest_success",
        "shield_rules": [
            {
                "id": "SHIELD-001",
                "pattern": "docs/*",
                "remark": "文档文件"
            }
        ],
        "mapping_rules": [
            {
                "id": "MAP-001",
                "source_pattern": "old_(.*)\\.py",
                "target_pattern": "new_\\1.py",
                "remark": "文件重命名"
            }
        ],
        "path_prefixes": [
            {
                "project_id": "target-1",
                "prefix": "/project"
            },
            {
                "project_id": "baseline-1",
                "prefix": "/baseline"
            }
        ]
    }


def main():
    """Entry point for CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
