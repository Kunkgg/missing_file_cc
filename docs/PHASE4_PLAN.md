# 阶段4：性能优化和CLI工具

## 目标

提供生产级别的性能优化和便捷的命令行工具，让系统能够高效处理大规模数据并方便日常使用。

## 核心任务

### 1. 并行处理优化 ⚡

**目标**: 充分利用多核CPU，提升大规模扫描性能

**实现内容**:
- 多个目标工程并行获取数据
- 多个基线工程并行获取数据
- 多个分析器并行执行
- 使用 `concurrent.futures.ThreadPoolExecutor` 或 `ProcessPoolExecutor`

**预期提升**:
- 多工程数据获取: 从串行 → 并行，**N倍速度提升**（N=工程数量）
- 分析器执行: 3个分析器并行，**~3倍速度提升**

### 2. CLI 命令行工具 🖥️

**目标**: 提供简单易用的命令行界面

**命令设计**:

```bash
# 基本扫描
missing-file-check scan --config config.yaml

# 从数据库加载配置
missing-file-check scan --task-id TASK-001

# 生成报告
missing-file-check report --task-id TASK-001 --output report.html

# 列出任务
missing-file-check list --status completed

# 查看统计
missing-file-check stats --task-id TASK-001

# 创建任务配置
missing-file-check init --output config.yaml

# 验证配置
missing-file-check validate --config config.yaml
```

**特性**:
- 进度条显示（使用 rich 库）
- 彩色输出
- 详细/简洁模式切换
- 错误友好提示
- 配置文件支持（YAML/JSON）

### 3. 性能测试和基准测试 📊

**目标**: 验证性能优化效果，建立性能基线

**测试场景**:
- 小规模: 100 vs 200 文件
- 中等规模: 10,000 vs 20,000 文件
- 大规模: 60,000 vs 200,000 文件（实际业务场景）

**测试维度**:
- 数据获取耗时
- 对比计算耗时
- 规则引擎耗时
- 总体耗时
- 内存占用
- CPU 使用率

### 4. 缓存机制 💾

**目标**: 减少重复数据获取，提升响应速度

**缓存内容**:
- API 响应缓存（带过期时间）
- 文件列表缓存
- 分析结果缓存

**实现方式**:
- 使用 `functools.lru_cache` 进行内存缓存
- 可选 Redis 缓存支持
- 智能缓存失效策略

### 5. 批处理和调度 ⏰

**目标**: 支持批量任务和定时调度

**功能**:
- 批量任务配置
- 任务队列管理
- 失败重试机制
- 邮件通知
- Webhook 回调

## 实施步骤

### Step 1: 并行处理框架

**文件**: `missing_file_check/utils/concurrent.py`

```python
class ParallelExecutor:
    """并行执行器，支持线程池和进程池"""

    def execute_parallel(self, tasks, max_workers=None):
        """并行执行多个任务"""
        pass
```

**更新**: `missing_file_check/scanner/checker.py`
- 并行获取目标工程数据
- 并行获取基线工程数据

### Step 2: CLI 命令行工具

**文件**: `missing_file_check/cli/__init__.py`

```python
@click.group()
def cli():
    """Missing File Check - 缺失文件扫描工具"""
    pass

@cli.command()
@click.option('--config', help='配置文件路径')
@click.option('--task-id', help='任务ID（从数据库加载）')
def scan(config, task_id):
    """执行扫描任务"""
    pass

@cli.command()
@click.option('--task-id', required=True)
@click.option('--output', default='report.html')
def report(task_id, output):
    """生成报告"""
    pass
```

### Step 3: 性能测试

**文件**: `tests/performance/test_benchmark.py`

```python
def test_large_scale_performance():
    """测试大规模数据处理性能"""
    # 60k vs 200k files
    pass

def test_parallel_speedup():
    """测试并行处理加速效果"""
    pass
```

### Step 4: 配置文件支持

**文件**: `missing_file_check/config/file_loader.py`

支持从 YAML/JSON 文件加载配置：

```yaml
# config.yaml
task_id: "TASK-001"
target_projects:
  - project_id: "target-1"
    project_type: "target_project_api"
    connection:
      api_endpoint: "https://api.example.com"
      token: "${API_TOKEN}"  # 支持环境变量
      project_key: "target-key"

baseline_projects:
  - project_id: "baseline-1"
    project_type: "baseline_project_api"
    connection:
      api_endpoint: "https://api.example.com"
      token: "${API_TOKEN}"
      project_key: "baseline-key"

baseline_selector_strategy: "latest_success_commit_id"

shield_rules:
  - id: "SHIELD-001"
    pattern: "docs/*"
    remark: "文档文件"

mapping_rules:
  - id: "MAP-001"
    source_pattern: "old_(.*)\\.py"
    target_pattern: "new_\\1.py"
    remark: "文件重命名"

path_prefixes:
  - project_id: "target-1"
    prefix: "/project"
  - project_id: "baseline-1"
    prefix: "/baseline"
```

### Step 5: 文档和示例

- CLI 使用文档
- 性能优化指南
- 最佳实践
- 故障排查

## 技术选型

### CLI 框架
- **Click**: 功能强大，易于使用
- **Rich**: 终端美化，进度条，表格

### 并发库
- **concurrent.futures**: Python 标准库，简单可靠
- **ThreadPoolExecutor**: I/O 密集型任务（API、FTP）
- **ProcessPoolExecutor**: CPU 密集型任务（可选）

### 配置文件
- **PyYAML**: YAML 解析
- **python-dotenv**: 环境变量支持

### 性能测试
- **pytest-benchmark**: 性能基准测试
- **memory_profiler**: 内存分析

## 验收标准

### 功能完整性
- ✅ CLI 所有命令正常工作
- ✅ 配置文件正确解析
- ✅ 并行执行正确性验证

### 性能指标
- ✅ 多工程并行获取速度提升 > 50%
- ✅ 大规模数据（60k vs 200k）处理时间 < 5分钟
- ✅ 内存占用 < 1GB

### 用户体验
- ✅ 命令行输出美观清晰
- ✅ 进度提示准确
- ✅ 错误信息友好
- ✅ 文档完整

## 时间估算

- 并行处理框架: 2-3小时
- CLI 工具基础: 3-4小时
- CLI 高级功能: 2-3小时
- 性能测试: 2-3小时
- 配置文件支持: 1-2小时
- 文档和示例: 1-2小时

**总计**: 约 11-17 小时

## 依赖包

```bash
# CLI 工具
uv add click rich

# 配置文件
uv add pyyaml python-dotenv

# 性能测试（开发依赖）
uv add --dev pytest-benchmark memory-profiler
```

## 后续优化（可选）

- 分布式任务执行（Celery）
- Web 界面（FastAPI + Vue）
- 监控和告警（Prometheus）
- 日志聚合（ELK）
- API 网关
