# 示例脚本目录

本目录包含演示项目功能的各种示例脚本。

## 示例列表

### 完整功能示例

- **example_phase3_complete.py** - 完整的端到端示例（阶段3完成版）
  - 演示配置加载、数据获取、扫描、分析、持久化、报告生成
  - 包含数据库集成和对象存储
  - 推荐作为主要参考示例

### 简化示例

- **example_simple_local.py** - 简化的本地文件适配器示例
  - 使用两个独立文件（build_info.json + files.csv/json）
  - 演示最简单的使用方式
  - 适合快速测试和理解基本流程

### 特定功能示例

- **example_usage.py** - 基本使用示例（阶段1）
  - 核心扫描功能演示
  - 不包含数据库和分析器

- **example_with_adapters.py** - 数据源适配器示例（阶段2）
  - 演示 API、FTP、Local 三种适配器
  - Mock 外部依赖

## 运行示例

```bash
# 运行完整示例
uv run python examples/example_phase3_complete.py

# 运行简化本地示例
uv run python examples/example_simple_local.py

# 运行基础示例
uv run python examples/example_usage.py

# 运行适配器示例
uv run python examples/example_with_adapters.py
```

## 注意事项

- 所有示例都使用 `test_data/` 目录中的测试数据
- 数据库相关示例需要先配置 `.env` 文件
- 部分示例使用 Mock 数据模拟外部服务
