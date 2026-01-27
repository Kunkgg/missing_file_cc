# 数据库设计评估和建议

## 原始设计分析

你的设计使用了**多态关联**模式，这是合理的。但需要补充一些信息和表。

## 建议的完整表结构

### 1. 任务主表（补充字段）

```sql
Table missing_file_tasks {
  id integer PK
  group_id integer
  search_version varchar
  product varchar
  tool varchar
  source_type varchar
  data_type varchar

  -- 新增：基线选择策略
  baseline_selector_strategy varchar DEFAULT 'latest_success'
  baseline_selector_params json  -- 存储策略参数 {"baseline_project_id": "xxx", ...}

  created_at datetime
  updated_at datetime
  is_active bool DEFAULT true
}
```

**说明**：
- `baseline_selector_strategy`: 存储6种策略之一（latest_success_commit_id, latest_success_version等）
- `baseline_selector_params`: JSON字段存储策略参数（如specific策略需要的project_id）

### 2. 工程关系表（改进版）

```sql
Table missing_file_project_relation {
  id integer PK
  task_id integer                     -- 关联 missing_file_tasks.id

  -- 改进：明确角色和平台
  role varchar                        -- "target" 或 "baseline"
  platform_type varchar               -- "platform_a", "platform_b", "baseline"
  project_id integer                  -- 指向对应平台表的ID

  -- 新增：存储适配器配置
  adapter_type varchar                -- "api", "ftp", "local"
  adapter_config json                 -- 存储connection配置

  created_at datetime

  -- 索引建议（应用层维护）
  INDEX idx_task_id (task_id)
  INDEX idx_role_platform (role, platform_type)
}
```

**说明**：
- `role`: 区分是target还是baseline
- `platform_type`: 标识具体平台，配合project_id使用
- `adapter_type` + `adapter_config`: 存储如何获取数据（API端点、FTP地址等）

**adapter_config示例**：
```json
{
  "api_endpoint": "https://api.example.com",
  "token": "***",
  "project_key": "PROJECT-1"
}
```

### 3. 路径前缀配置表（新增）

```sql
Table missing_file_path_prefixes {
  id integer PK
  task_id integer
  project_relation_id integer         -- 关联 missing_file_project_relation.id
  prefix varchar                      -- 如 "/workspace/project"
  created_at datetime

  INDEX idx_task_id (task_id)
}
```

### 4. 屏蔽规则表（新增）

```sql
Table missing_file_shield_rules {
  id integer PK
  task_id integer
  rule_id varchar                     -- 用户定义的规则ID，如 "SHIELD-001"
  pattern varchar                     -- 匹配模式
  remark varchar                      -- 规则说明
  enabled bool DEFAULT true           -- 是否启用（加载时过滤）
  created_at datetime
  updated_at datetime

  INDEX idx_task_id (task_id)
  INDEX idx_enabled (task_id, enabled)
}
```

### 5. 映射规则表（新增）

```sql
Table missing_file_mapping_rules {
  id integer PK
  task_id integer
  rule_id varchar                     -- 用户定义的规则ID，如 "MAP-001"
  source_pattern varchar              -- 源路径模式
  target_pattern varchar              -- 目标路径模式
  remark varchar
  enabled bool DEFAULT true
  created_at datetime
  updated_at datetime

  INDEX idx_task_id (task_id)
  INDEX idx_enabled (task_id, enabled)
}
```

### 6. 扫描结果表（新增）

```sql
Table missing_file_scan_results {
  id integer PK
  task_id integer

  -- 扫描状态
  status varchar                      -- "running", "completed", "failed"
  error_message text                  -- 失败时的错误信息

  -- 统计信息
  total_missing integer
  missed_count integer
  shielded_count integer
  remapped_count integer
  failed_count integer

  -- 工程信息
  target_project_ids json             -- ["proj1", "proj2"]
  baseline_project_ids json           -- ["base1", "base2"]

  -- 报告
  report_url varchar                  -- 对象存储URL
  report_generated_at datetime

  -- 时间戳
  started_at datetime
  completed_at datetime
  created_at datetime

  INDEX idx_task_id (task_id)
  INDEX idx_status (status)
  INDEX idx_created_at (created_at)
}
```

### 7. 缺失文件详情表（新增）

```sql
Table missing_file_details {
  id integer PK
  scan_result_id integer              -- 关联 missing_file_scan_results.id

  -- 文件信息
  file_path varchar                   -- 归一化后的路径
  status varchar                      -- "missed", "shielded", "remapped", "failed"
  source_baseline_project varchar     -- 来自哪个基线工程

  -- 屏蔽信息
  shielded_by varchar
  shielded_remark varchar

  -- 映射信息
  remapped_by varchar
  remapped_to varchar
  remapped_remark varchar

  -- 分析信息（阶段3填充）
  ownership varchar                   -- 文件归属（团队/负责人）
  miss_reason varchar                 -- 缺失原因
  first_detected_at datetime          -- 首次发现时间

  created_at datetime

  INDEX idx_scan_result_id (scan_result_id)
  INDEX idx_status (status)
  INDEX idx_file_path (file_path)
}
```

### 8. 平台表（保持原样）

```sql
-- 平台A目标工程
Table platform_a_target_project {
  id integer PK
  project_name varchar
  c_version varchar
  -- 可能还有其他字段
}

-- 平台B目标工程
Table platform_b_target_project {
  id integer PK
  job_name varchar
  branch varchar
  -- 可能还有其他字段
}

-- 基线工程
Table baseline_project {
  id integer PK
  data_source varchar
  project_name varchar
  c_version varchar
  job_name varchar
  -- 可能还有其他字段
}
```

## 关系图

```
missing_file_tasks (1)
  ├─→ (N) missing_file_project_relation
  │         └─→ (1) platform_a_target_project / platform_b_target_project / baseline_project
  ├─→ (N) missing_file_path_prefixes
  ├─→ (N) missing_file_shield_rules
  ├─→ (N) missing_file_mapping_rules
  └─→ (N) missing_file_scan_results
            └─→ (N) missing_file_details
```

## 数据加载流程

### 加载TaskConfig

```python
# 1. 加载任务基本信息
task = query("SELECT * FROM missing_file_tasks WHERE id = ?", task_id)

# 2. 加载工程关系
relations = query("""
    SELECT * FROM missing_file_project_relation
    WHERE task_id = ?
""", task_id)

# 3. 根据platform_type加载具体工程信息
target_projects = []
for rel in relations where role='target':
    if rel.platform_type == 'platform_a':
        proj = query("SELECT * FROM platform_a_target_project WHERE id = ?", rel.project_id)
    elif rel.platform_type == 'platform_b':
        proj = query("SELECT * FROM platform_b_target_project WHERE id = ?", rel.project_id)

    # 组装ProjectConfig
    config = ProjectConfig(
        project_id=str(rel.project_id),
        project_name=proj.project_name,
        project_type=ProjectType[rel.adapter_type.upper()],
        connection=json.loads(rel.adapter_config)
    )
    target_projects.append(config)

# 4. 加载基线工程（类似）
baseline_projects = ...

# 5. 加载规则
shield_rules = query("""
    SELECT * FROM missing_file_shield_rules
    WHERE task_id = ? AND enabled = true
""", task_id)

mapping_rules = query("""
    SELECT * FROM missing_file_mapping_rules
    WHERE task_id = ? AND enabled = true
""", task_id)

# 6. 加载路径前缀
path_prefixes = query("""
    SELECT * FROM missing_file_path_prefixes
    WHERE task_id = ?
""", task_id)

# 7. 组装TaskConfig
task_config = TaskConfig(
    task_id=str(task.id),
    target_projects=target_projects,
    baseline_projects=baseline_projects,
    baseline_selector_strategy=task.baseline_selector_strategy,
    baseline_selector_params=json.loads(task.baseline_selector_params) if task.baseline_selector_params else None,
    shield_rules=[ShieldRule(**r) for r in shield_rules],
    mapping_rules=[MappingRule(**r) for r in mapping_rules],
    path_prefixes=[PathPrefixConfig(**p) for p in path_prefixes]
)
```

## 关键设计决策

### 1. 多态关联
通过 `role` + `platform_type` + `project_id` 组合实现多态，应用层负责维护一致性。

### 2. JSON字段
使用JSON存储灵活配置（adapter_config, baseline_selector_params），避免频繁修改表结构。

### 3. enabled字段
规则表使用enabled字段，加载时过滤，避免物理删除。

### 4. 索引策略
虽然不建外键，但建议添加索引提高查询性能（通过注释标注）。

## 建议补充的字段

### missing_file_tasks
- `baseline_selector_strategy` - 基线选择策略
- `baseline_selector_params` - 策略参数（JSON）

### missing_file_project_relation
- `role` - 区分target/baseline
- `platform_type` - 明确平台类型
- `adapter_type` - 适配器类型
- `adapter_config` - 适配器配置（JSON）

### 新增表
- `missing_file_path_prefixes` - 路径前缀
- `missing_file_shield_rules` - 屏蔽规则
- `missing_file_mapping_rules` - 映射规则
- `missing_file_scan_results` - 扫描结果
- `missing_file_details` - 缺失文件详情

## 优点

1. **灵活性**: JSON字段允许配置灵活变化
2. **扩展性**: 新增平台只需添加新表
3. **性能**: 合理的索引策略
4. **清晰性**: 明确的角色和类型划分
5. **历史追踪**: 完整的时间戳记录

## 注意事项

1. **应用层约束**: 由于无外键，需要在应用层严格保证数据一致性
2. **JSON查询**: 如需频繁查询JSON字段内容，考虑提取为独立字段
3. **数据清理**: 需要应用层实现级联删除逻辑
4. **事务管理**: 多表操作需要使用事务保证原子性

## 总结

你的原始设计思路正确，建议补充：
1. ✅ 基线选择策略字段
2. ✅ 工程关系表增加role和platform_type
3. ✅ 适配器配置字段
4. ✅ 规则表（屏蔽、映射）
5. ✅ 路径前缀表
6. ✅ 扫描结果和详情表

这样就可以完整支持整个系统的功能了。
