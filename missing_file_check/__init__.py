"""
缺失文件扫描工具 - 主包

白盒安全防护组件，用于检测扫描过程中的缺失文件。
"""

__version__ = "0.1.0"
__author__ = "Security Team"

from missing_file_check.core.checker import MissingFileChecker

__all__ = ["MissingFileChecker"]
