我有下面几点疑问和需要讨论的地方， 希望你能帮我解答：

1. ProjectConfig.project_type 应该是一个枚举类型 ProjectType, 包含以下几种类型：

```
ProjectType
  ├── TARGET_PROJECT_API
  ├── BASELINE_PROJECT_API
  ├── FTP
  └── LOCAL
```

2. ShieldRule 和 MappingRule 是否应该 `enabled` 这个属性， 一般来说加载配置信息的时候就应该过滤掉未启用的屏蔽和路径映射规则
3. ProjectConfig.connection 字段应该包含什么内容， 不同的 project_type 可能需要不同的连接信息， 可以举几个简单的例子么？
4. ProjectScanResult 需要包含构建任务信息:
```
  ├── build_info (任务信息)
     ├── build_no
     ├── build_status
     ├── branch
     ├── commit_id
     ├── b_version
     ├── build_url
     ├── start_time
     └── end_time
```
5. CheckResult 中 target_project_id 和 baseline_project_id 应该为 List[str]
6. MissingFile.status 补充一种状态 failed, 表示在待检查工程文件列表中存在但状态为 failed
7. 请解释 ProjectScanResult.branch_node 的作用是什么？
8. 不需要使用排列组合的方式对比待检查工程和基线工程, 只需要使用待检查共文件列表的全集和基线工程文件列表的全集进行一次对比。需要最后能标记初缺失文件来自哪个基线工程
9. 由于基线工程的查询可能需要依赖待检查工程的部分工程信息， 需要引入基线工程选择策略, BaselineSelector 实现基线工程的匹配选择方式, 已知的基线工程匹配选择方式有这几种:
  1. 全部基线工程最新一次成功并且 commit_id 和待检查工程相同
  2. 全部基线最新一次成功并且 b_version 和待检查工程相同
  3. 最新一次成功, 并且仅指定基线工程和指定待检查工程 commit_id 相同
  4. 最新一次成功, 并且仅指定基线工程和指定待检查工程 b_version 相同
  5. 最新一次成功
  6. 不做任何匹配限制




