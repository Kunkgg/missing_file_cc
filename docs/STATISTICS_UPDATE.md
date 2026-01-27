# 统计字段更新说明

## 更新背景

基于业务实际需求，对 `ResultStatistics` 数据结构进行了优化：

**核心理念**：
- **需要处理的问题**: `missed` 和 `failed` 两种状态
- **已审核通过的**: `shielded` 和 `remapped` 不是问题，是经过审核的正常情况

因此统计信息需要明确区分"需要关注的问题"和"已审核通过"。

## 字段变更

### 移除字段

- `total_missing` - 总缺失文件数（不再需要）

### 新增字段

1. **passed_count** (int) - 已通过数量
   - 计算方式：`shielded_count + remapped_count`
   - 含义：经过审核确认不是问题的文件数

2. **target_file_count** (int) - 目标工程文件总数
   - 所有目标工程的文件数量总和

3. **baseline_file_count** (int) - 基线工程文件总数
   - 所有基线工程的文件数量总和

### 保留字段

1. **missed_count** (int) - 真实缺失文件数（🚨 需要处理）
2. **failed_count** (int) - 扫描失败文件数（🚨 需要处理）
3. **shielded_count** (int) - 屏蔽文件数（✅ 已审核）
4. **remapped_count** (int) - 映射文件数（✅ 已审核）
5. **target_project_count** (int) - 目标工程数量
6. **baseline_project_count** (int) - 基线工程数量

## 新的统计结构

```python
@dataclass
class ResultStatistics:
    """Statistics summary for a check result.

    Note: Only missed and failed are actual issues that need attention.
    Shielded and remapped files have been reviewed and are not problems.
    """

    missed_count: int  # Real issue: files missing in target
    failed_count: int  # Real issue: files exist but failed in target
    passed_count: int  # Not issues: shielded + remapped (reviewed and approved)
    shielded_count: int  # Subset of passed: excluded by shield rules
    remapped_count: int  # Subset of passed: handled by path mapping
    target_file_count: int  # Total files in target projects
    baseline_file_count: int  # Total files in baseline projects
    target_project_count: int  # Number of target projects
    baseline_project_count: int  # Number of baseline projects
```

## 报告展示变更

### HTML 报告

原来：
```
总缺失文件: 100
├─ 真实缺失: 50
├─ 已屏蔽: 30
├─ 已映射: 15
└─ 扫描失败: 5
```

现在：
```
🚨 需要处理的问题:
   ├─ 🔴 真实缺失: 50
   └─ ❌ 扫描失败: 5

✅ 已审核通过: 45
   ├─ 🛡️  已屏蔽: 30
   └─ 🔄 已映射: 15

📁 文件数量统计:
   ├─ 目标工程文件: 10000
   ├─ 基线工程文件: 10100
   ├─ 目标工程数: 2
   └─ 基线工程数: 1
```

### JSON 报告

```json
{
  "statistics": {
    "missed_count": 50,
    "failed_count": 5,
    "passed_count": 45,
    "shielded_count": 30,
    "remapped_count": 15,
    "target_file_count": 10000,
    "baseline_file_count": 10100,
    "target_project_count": 2,
    "baseline_project_count": 1
  }
}
```

## 数据库表变更

### missing_file_scan_results 表

**移除列**:
- `total_missing` INT

**新增列**:
- `passed_count` INT DEFAULT 0
- `target_file_count` INT DEFAULT 0
- `baseline_file_count` INT DEFAULT 0
- `target_project_count` INT DEFAULT 0
- `baseline_project_count` INT DEFAULT 0

## 迁移步骤

### 1. 运行迁移脚本

```bash
uv run python scripts/migrate_statistics.py
```

迁移脚本会：
1. 添加新的统计列
2. 根据现有数据计算 `passed_count = shielded_count + remapped_count`
3. 删除 `total_missing` 列

### 2. 更新依赖代码

如果你有自定义代码使用了 `total_missing` 字段，需要更新：

**Before**:
```python
print(f"Total missing: {result.statistics.total_missing}")
```

**After**:
```python
# 如果需要显示问题总数
issues = result.statistics.missed_count + result.statistics.failed_count
print(f"Issues: {issues}")

# 或者分别显示
print(f"Missed: {result.statistics.missed_count}")
print(f"Failed: {result.statistics.failed_count}")
print(f"Passed: {result.statistics.passed_count}")
```

## 受影响的文件

### 核心模块
- `missing_file_check/scanner/checker.py` - ResultStatistics 定义和计算
- `missing_file_check/storage/models.py` - ORM 模型
- `missing_file_check/storage/repository.py` - 数据库保存逻辑
- `missing_file_check/storage/report_generator.py` - 报告生成

### 示例脚本
- `examples/example_simple_local.py`
- `examples/example_usage.py`
- `examples/example_with_adapters.py`
- `examples/example_phase3_complete.py`

### 测试文件
- `tests/test_phase3.py` - 所有 ResultStatistics 构造调用

### 工具脚本
- `scripts/migrate_statistics.py` - 新增数据库迁移脚本

## 向后兼容性

**不兼容变更**：
- `ResultStatistics` 构造函数参数顺序和数量已改变
- `total_missing` 字段已移除
- 数据库表结构需要迁移

**升级影响**：
- 所有使用 `ResultStatistics` 的代码需要更新
- 现有数据库需要运行迁移脚本
- 旧版本的 HTML/JSON 报告格式会有变化

## 测试验证

所有 38 个测试用例已更新并通过：

```bash
uv run pytest tests/ -v
# 38 passed ✅
```

## 业务价值

1. **更清晰的问题优先级**：
   - 直接看到需要处理的问题数量（missed + failed）
   - 已审核的文件不会干扰问题统计

2. **更完整的上下文信息**：
   - 文件总数帮助理解扫描覆盖范围
   - 工程数量帮助理解扫描规模

3. **更好的决策支持**：
   - 可以计算缺失率：`missed_count / baseline_file_count`
   - 可以评估审核覆盖：`passed_count / (missed_count + failed_count + passed_count)`

## 后续建议

1. **监控指标**：
   - 关注 `missed_count` 和 `failed_count` 的趋势
   - 跟踪 `passed_count` 占比，评估规则有效性

2. **告警阈值**：
   - 设置 `missed_count + failed_count` 的告警阈值
   - 忽略 `passed_count`，避免误报

3. **报表展示**：
   - 仪表盘优先展示"需要处理的问题"
   - "已审核通过"可以折叠或作为次要信息

---

**更新日期**: 2026-01-27
**影响范围**: 核心统计逻辑、数据库、报告、测试
**破坏性变更**: 是
**需要迁移**: 是
