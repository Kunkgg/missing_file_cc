# Missing File Check - 缺失文件扫描工具

白盒安全扫描工具，用于检测代码扫描过程中的缺失文件。通过对比目标工程和基线工程的文件列表，识别应该扫描但未扫描的文件，确保安全扫描的完整覆盖。

## 项目状态

- ✅ **阶段1完成**: 基础架构 (7个核心模块, 1801行代码, 13个测试)
- ✅ **阶段2完成**: 数据源支持 (3个适配器, 1380行代码, 9个测试)
- 📦 **阶段3待开发**: 结果分析
- 📦 **阶段4待开发**: 集成优化

**总计**: 3205行代码，22个测试全部通过 ✅

## 快速开始

### 安装

```bash
# 安装依赖
uv sync

# 运行示例
uv run python example_with_adapters.py

# 运行测试
uv run pytest tests/ -v
```

### 基本使用

```python
from missing_file_check.config.models import (
    TaskConfig,
    ProjectConfig,
    ProjectType,
    ShieldRule,
    MappingRule,
    PathPrefixConfig,
)
from missing_file_check.scanner.checker import MissingFileChecker

# 配置任务
config = TaskConfig(
    task_id="TASK-001",
    target_projects=[
        ProjectConfig(
            project_id="target-1",
            project_name="待检查工程",
            project_type=ProjectType.TARGET_PROJECT_API,
            connection={
                "api_endpoint": "https://api.example.com",
                "token": "your-token",
                "project_key": "TARGET-1"
            }
        )
    ],
    baseline_projects=[
        ProjectConfig(
            project_id="baseline-1",
            project_name="基线工程",
            project_type=ProjectType.BASELINE_PROJECT_API,
            connection={
                "api_endpoint": "https://api.example.com",
                "token": "your-token",
                "project_key": "BASELINE-1"
            }
        )
    ],
    baseline_selector_strategy="latest_success_commit_id",
    shield_rules=[
        ShieldRule(id="S1", pattern="docs/*", remark="文档文件")
    ],
    mapping_rules=[
        MappingRule(
            id="M1",
            source_pattern=r"old/(.+)",
            target_pattern=r"new/\1",
            remark="目录迁移"
        )
    ],
    path_prefixes=[
        PathPrefixConfig(project_id="target-1", prefix="/workspace/project"),
        PathPrefixConfig(project_id="baseline-1", prefix="/workspace/baseline"),
    ],
)

# 执行检查
checker = MissingFileChecker(config)
result = checker.check()

# 查看结果
print(f"总缺失文件: {result.statistics.total_missing}")
print(f"  - 真实缺失: {result.statistics.missed_count}")
print(f"  - 已屏蔽: {result.statistics.shielded_count}")
print(f"  - 已映射: {result.statistics.remapped_count}")
print(f"  - 扫描失败: {result.statistics.failed_count}")
```

## 核心特性

### 1. 支持多种数据源

- ✅ **API** - REST API接口 (TARGET_PROJECT_API, BASELINE_PROJECT_API)
- ✅ **FTP** - FTP服务器下载
- ✅ **Local** - 本地JSON文件

### 2. 灵活的基线选择策略

- `latest_success_commit_id` - 最新成功 + commit_id匹配
- `latest_success_version` - 最新成功 + 版本号匹配
- `specific_baseline_commit_id` - 指定基线和目标 commit_id匹配
- `specific_baseline_version` - 指定基线和目标版本匹配
- `latest_success` - 最新成功（无匹配条件）
- `no_restriction` - 无限制

### 3. 智能文件分类

系统将文件分为4种状态：

- **missed** - 基线有，目标没有（真实缺失）
- **shielded** - 被屏蔽规则排除
- **remapped** - 路径映射匹配（文件重命名/移动）
- **failed** - 目标中存在但扫描失败

### 4. 强大的规则引擎

#### 屏蔽规则（Shield Rules）
```python
# 支持 glob 和正则表达式
ShieldRule(id="S1", pattern="docs/*")              # glob
ShieldRule(id="S2", pattern=r".*\.log$")           # regex
ShieldRule(id="S3", pattern="test_*.py")           # glob
```

#### 映射规则（Mapping Rules）
```python
# 使用正则表达式捕获组
MappingRule(
    id="M1",
    source_pattern=r"old_(.+)\.py",
    target_pattern=r"new_\1.py"
)
# old_file.py → new_file.py

MappingRule(
    id="M2",
    source_pattern=r"(.+)/tests/test_(.+)\.py",
    target_pattern=r"\1/test/\2_test.py"
)
# app/tests/test_main.py → app/test/main_test.py
```

### 5. 高性能对比算法

- **O(n)复杂度**: 使用集合运算
- **全集对比**: 不是M×N次对比，而是一次完成
- **来源追踪**: 每个缺失文件标记来自哪个基线工程
- **适用规模**:
  - 目标工程: 200,000+ 文件
  - 基线工程: 60,000+ 文件

## 架构设计

### 模块结构

```
missing_file_check/
├── config/              # 配置层 - Pydantic验证
│   ├── models.py        # 配置数据模型
│   └── loader.py        # 配置加载器
├── adapters/            # 适配器层 - 统一数据源访问
│   ├── base.py          # 基类和接口
│   ├── factory.py       # 工厂模式
│   ├── api_adapter.py   # API适配器 ✨
│   ├── ftp_adapter.py   # FTP适配器 ✨
│   └── local_adapter.py # 本地文件适配器 ✨
├── selectors/           # 选择器层 - 基线工程选择
│   ├── base.py          # 选择器基类
│   ├── strategies.py    # 6种选择策略
│   └── factory.py       # 策略工厂
├── scanner/             # 扫描层 - 核心对比和规则引擎
│   ├── normalizer.py    # 路径归一化
│   ├── merger.py        # 文件列表合并
│   ├── comparator.py    # 集合对比
│   ├── rule_engine.py   # 规则引擎
│   └── checker.py       # 主检查器
├── analyzers/           # 分析层 (阶段3)
├── storage/             # 持久化层 (阶段3)
└── utils/               # 工具层 (阶段4)
```

### 数据流

```
配置加载 → 适配器 → 基线选择 → 文件合并 → 对比 → 规则引擎 → 结果
```

## 技术栈

- **Python 3.13+** (使用 uv 管理)
- **Pydantic** - 数据验证
- **Requests** - API调用
- **Pytest** - 测试框架

## 开发命令

```bash
# 安装依赖
uv sync

# 运行主程序
uv run python main.py

# 添加新依赖
uv add <package-name>

# 运行测试
uv run pytest tests/ -v

# 运行特定测试
uv run pytest tests/test_adapters.py -v

# 代码覆盖率
uv run pytest tests/ --cov=missing_file_check
```

## 示例输出

```
📈 Statistics:
   Total Missing Files: 6
   ├─ 🔴 Missed: 3        src/database.py, tests/test_utils.py, ...
   ├─ 🛡️  Shielded: 2     docs/API.md, docs/README.md
   ├─ 🔄 Remapped: 0
   └─ ❌ Failed: 1        tests/test_main.py

🔴 Missed Files (3):
   • src/database.py
     Source: baseline-project
   • tests/test_utils.py
     Source: baseline-project

🛡️  Shielded Files (2):
   • docs/API.md
     Rule: SHIELD-DOCS-001
     Reason: Documentation files are excluded from scanning

❌ Failed Files (1):
   • tests/test_main.py
     Status: File exists but scan failed
     Source: baseline-project
```

## 文档

- 📘 [快速开始指南](QUICK_START.md) - 基本使用方法
- 📗 [阶段1总结](IMPLEMENTATION_SUMMARY.md) - 基础架构实现
- 📕 [阶段2总结](PHASE2_SUMMARY.md) - 数据源适配器实现
- 📙 [架构实现](ARCHITECTURE_IMPLEMENTED.md) - 详细架构文档
- 📔 [CLAUDE指令](CLAUDE.md) - Claude Code开发指南

## 扩展性

### 添加自定义适配器

```python
from missing_file_check.adapters.base import ProjectAdapter
from missing_file_check.adapters.factory import AdapterFactory

class CustomAdapter(ProjectAdapter):
    def fetch_files(self, commit_id=None, b_version=None):
        # 你的自定义逻辑
        pass

# 注册
AdapterFactory.register(ProjectType.CUSTOM, CustomAdapter)
```

### 添加自定义基线选择策略

```python
from missing_file_check.selectors.base import BaselineSelector
from missing_file_check.selectors.factory import BaselineSelectorFactory

class MySelector(BaselineSelector):
    def select(self, baseline_configs, target_results):
        # 你的自定义选择逻辑
        pass

# 注册
BaselineSelectorFactory.register("my_strategy", MySelector)
```

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 测试结果
============================== 22 passed ==============================

tests/test_core_functionality.py (13 tests)
  ✓ Path normalization
  ✓ File merging
  ✓ File comparison
  ✓ Rule engine
  ✓ Config validation

tests/test_adapters.py (9 tests)
  ✓ Local adapter
  ✓ API adapter with mocks
  ✓ FTP adapter with mocks
  ✓ Adapter factory
```

## 设计原则

- ✅ **可扩展规则** - 工厂模式 + 策略模式
- ✅ **清晰的扫描流程** - 7个模块职责明确
- ✅ **规则解耦** - 固定执行顺序，无依赖
- ✅ **易于测试** - 依赖注入，Mock支持
- ✅ **简洁接口** - 避免过度设计

## 贡献者

开发工具: Claude Code (claude.ai/code)

## 许可证

内部项目，用于公司白盒安全防护体系。

## 联系方式

如需帮助或反馈问题，请查阅文档或联系开发团队。
