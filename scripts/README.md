# 工具脚本目录

本目录包含项目相关的工具脚本和辅助程序。

## 脚本列表

### 数据库工具

- **create_tables.py** - 数据库表创建脚本
  - 使用 SQLAlchemy 创建所有数据库表
  - 支持从 `.env` 文件读取数据库配置
  - 支持命令行参数指定配置

## 使用方法

### 创建数据库表

```bash
# 使用 .env 文件配置
uv run python scripts/create_tables.py

# 或使用命令行参数
uv run python scripts/create_tables.py \
  --host localhost \
  --port 3306 \
  --user root \
  --password your_password \
  --database missing_file_check
```

## 配置要求

运行数据库相关脚本前，请确保：

1. 已安装 MySQL 数据库
2. 已创建目标数据库
3. 配置了 `.env` 文件或准备好命令行参数

`.env` 文件示例：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=missing_file_check
```
