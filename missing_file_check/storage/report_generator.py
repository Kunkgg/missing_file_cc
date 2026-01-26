"""
Report generator for creating HTML and JSON reports.

Generates comprehensive reports from CheckResult data.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Template

from missing_file_check.scanner.checker import CheckResult


class ReportGenerator:
    """Generator for HTML and JSON reports."""

    # HTML template embedded in code for simplicity
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>缺失文件扫描报告 - {{ result.task_id }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 32px; margin-bottom: 10px; }
        .header .meta { opacity: 0.9; font-size: 14px; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border-left: 4px solid #667eea;
        }
        .stat-card.missed { border-left-color: #f56565; }
        .stat-card.shielded { border-left-color: #48bb78; }
        .stat-card.remapped { border-left-color: #4299e1; }
        .stat-card.failed { border-left-color: #ed8936; }
        .stat-number { font-size: 36px; font-weight: bold; color: #667eea; }
        .stat-label { color: #718096; margin-top: 5px; }

        .section {
            background: white;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }

        .file-list { list-style: none; }
        .file-item {
            padding: 15px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            margin-bottom: 10px;
            transition: all 0.2s;
        }
        .file-item:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-color: #cbd5e0;
        }
        .file-path {
            font-family: "Monaco", "Menlo", "Courier New", monospace;
            color: #2d3748;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .file-meta {
            font-size: 13px;
            color: #718096;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge.missed { background: #fed7d7; color: #c53030; }
        .badge.shielded { background: #c6f6d5; color: #2f855a; }
        .badge.remapped { background: #bee3f8; color: #2c5282; }
        .badge.failed { background: #feebc8; color: #c05621; }

        .footer {
            text-align: center;
            color: #a0aec0;
            margin-top: 40px;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 缺失文件扫描报告</h1>
            <div class="meta">
                任务ID: {{ result.task_id }} |
                扫描时间: {{ result.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ result.statistics.total_missing }}</div>
                <div class="stat-label">总缺失文件</div>
            </div>
            <div class="stat-card missed">
                <div class="stat-number">{{ result.statistics.missed_count }}</div>
                <div class="stat-label">🔴 真实缺失</div>
            </div>
            <div class="stat-card shielded">
                <div class="stat-number">{{ result.statistics.shielded_count }}</div>
                <div class="stat-label">🛡️ 已屏蔽</div>
            </div>
            <div class="stat-card remapped">
                <div class="stat-number">{{ result.statistics.remapped_count }}</div>
                <div class="stat-label">🔄 已映射</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-number">{{ result.statistics.failed_count }}</div>
                <div class="stat-label">❌ 扫描失败</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 工程信息</h2>
            <p><strong>待检查工程:</strong> {{ result.target_project_ids|join(', ') }}</p>
            <p style="margin-top: 10px;"><strong>基线工程:</strong> {{ result.baseline_project_ids|join(', ') }}</p>
        </div>

        {% for status, title, emoji in [('missed', '真实缺失文件', '🔴'), ('shielded', '已屏蔽文件', '🛡️'), ('remapped', '已映射文件', '🔄'), ('failed', '扫描失败文件', '❌')] %}
        {% set files = result.missing_files|selectattr('status', 'equalto', status)|list %}
        {% if files %}
        <div class="section">
            <h2>{{ emoji }} {{ title }} ({{ files|length }})</h2>
            <ul class="file-list">
            {% for file in files %}
                <li class="file-item">
                    <div class="file-path">{{ file.path }}</div>
                    <div class="file-meta">
                        <span class="badge {{ status }}">{{ status|upper }}</span>
                        {% if file.source_baseline_project %}
                        <span>📦 来源: {{ file.source_baseline_project }}</span>
                        {% endif %}
                        {% if file.ownership %}
                        <span>👤 归属: {{ file.ownership }}</span>
                        {% endif %}
                        {% if file.miss_reason %}
                        <span>💡 原因: {{ file.miss_reason }}</span>
                        {% endif %}
                        {% if file.shielded_remark %}
                        <span>🛡️ {{ file.shielded_remark }}</span>
                        {% endif %}
                        {% if file.remapped_to %}
                        <span>🔄 映射到: {{ file.remapped_to }}</span>
                        {% endif %}
                        {% if file.first_detected_at %}
                        <span>🕒 首次发现: {{ file.first_detected_at.strftime('%Y-%m-%d') }}</span>
                        {% endif %}
                    </div>
                </li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}
        {% endfor %}

        <div class="footer">
            <p>缺失文件扫描工具 | 生成时间: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}</p>
        </div>
    </div>
</body>
</html>
    """

    def __init__(self, template_path: Optional[Path] = None):
        """
        Initialize report generator.

        Args:
            template_path: Optional path to custom HTML template
        """
        if template_path and template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                self.html_template = Template(f.read())
        else:
            self.html_template = Template(self.HTML_TEMPLATE)

    def generate_html(self, result: CheckResult, output_path: Optional[Path] = None) -> str:
        """
        Generate HTML report.

        Args:
            result: CheckResult from scanner
            output_path: Optional path to save HTML file

        Returns:
            Generated HTML content
        """
        html_content = self.html_template.render(
            result=result,
            datetime=datetime,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        return html_content

    def generate_json(self, result: CheckResult, output_path: Optional[Path] = None) -> str:
        """
        Generate JSON report.

        Args:
            result: CheckResult from scanner
            output_path: Optional path to save JSON file

        Returns:
            Generated JSON content
        """
        # Convert CheckResult to JSON-serializable dict
        report_data = {
            "task_id": result.task_id,
            "timestamp": result.timestamp.isoformat(),
            "statistics": {
                "total_missing": result.statistics.total_missing,
                "missed_count": result.statistics.missed_count,
                "shielded_count": result.statistics.shielded_count,
                "remapped_count": result.statistics.remapped_count,
                "failed_count": result.statistics.failed_count,
                "target_project_count": result.statistics.target_project_count,
                "baseline_project_count": result.statistics.baseline_project_count,
            },
            "target_projects": result.target_project_ids,
            "baseline_projects": result.baseline_project_ids,
            "missing_files": [
                {
                    "path": file.path,
                    "status": file.status,
                    "source_baseline_project": file.source_baseline_project,
                    "shielded_by": file.shielded_by,
                    "shielded_remark": file.shielded_remark,
                    "remapped_by": file.remapped_by,
                    "remapped_to": file.remapped_to,
                    "remapped_remark": file.remapped_remark,
                    "ownership": file.ownership,
                    "miss_reason": file.miss_reason,
                    "first_detected_at": file.first_detected_at.isoformat()
                    if file.first_detected_at
                    else None,
                }
                for file in result.missing_files
            ],
        }

        json_content = json.dumps(report_data, ensure_ascii=False, indent=2)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_content)

        return json_content

    def generate_both(
        self,
        result: CheckResult,
        html_path: Optional[Path] = None,
        json_path: Optional[Path] = None,
    ) -> tuple:
        """
        Generate both HTML and JSON reports.

        Args:
            result: CheckResult from scanner
            html_path: Optional path to save HTML file
            json_path: Optional path to save JSON file

        Returns:
            Tuple of (html_content, json_content)
        """
        html_content = self.generate_html(result, html_path)
        json_content = self.generate_json(result, json_path)

        return html_content, json_content
