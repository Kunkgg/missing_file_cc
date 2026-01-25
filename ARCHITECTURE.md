# 缺失文件扫描工具 - 架构设计文档

## 1. 系统模块划分

### 1.1 核心模块层次结构

```
missing_file_check/
├── core/                      # 核心业务逻辑层
│   ├── checker.py            # 主检查引擎
│   ├── comparator.py         # 文件对比器
│   ├── result_builder.py     # 结果构建器
│   └── task_executor.py      # 任务执行器（多对多关系处理）
│
├── config/                    # 配置管理层
│   ├── loader.py             # 配置加载器
│   ├── models.py             # 配置数据模型
│   ├── validator.py          # 配置验证器
│   └── cache.py              # 配置缓存
│
├── data/                      # 数据获取层
│   ├── adapters/             # 工程适配器（处理不同类型工程）
│   │   ├── base.py          # 工程适配器基类
│   │   ├── api_adapter.py   # API工程适配器（平台接口）
│   │   ├── ftp_adapter.py   # FTP工程适配器（离线FTP日志）
│   │   ├── file_adapter.py  # 文件工程适配器（本地文件）
│   │   └── platform_adapters/ # 不同检查平台的适配器
│   │       ├── platform_a.py  # 平台A适配器
│   │       ├── platform_b.py  # 平台B适配器
│   │       └── ...
│   ├── factory.py            # 工程工厂（根据类型创建适配器）
│   ├── fetcher.py           # 数据获取器（统一接口）
│   └── models.py            # 数据模型（文件列表、任务信息等）
│
├── path/                      # 路径处理层
│   ├── normalizer.py         # 路径归一化器
│   ├── matcher.py            # 路径匹配器（屏蔽、映射）
│   ├── trie.py              # 前缀树实现
│   └── rules.py             # 路径规则编译器
│
├── analysis/                  # 结果分析层
│   ├── ownership.py          # 文件归属分析
│   ├── reason_classifier.py  # 缺失原因分类器
│   ├── history_tracker.py    # 历史追踪器
│   └── async_analyzer.py     # 异步分析任务管理
│
├── storage/                   # 持久化层
│   ├── database/             # 数据库操作
│   │   ├── repository.py    # 数据仓库（CRUD）
│   │   ├── models.py        # ORM模型
│   │   └── migrations/      # 数据库迁移
│   ├── report/              # 报告生成
│   │   ├── generator.py     # 报告生成器
│   │   ├── templates/       # 报告模板
│   │   └── uploader.py      # 对象存储上传器
│   └── cache/               # 缓存层
│       ├── redis_cache.py   # Redis缓存实现
│       └── memory_cache.py  # 内存缓存实现
│
├── utils/                     # 工具层
│   ├── concurrent.py         # 并发处理工具
│   ├── batch.py             # 批处理工具
│   ├── metrics.py           # 指标收集器
│   ├── logger.py            # 日志工具
│   └── retry.py             # 重试机制
│
└── cli/                       # 命令行接口层
    ├── commands.py           # CLI命令
    ├── output.py            # 输出格式化
    └── progress.py          # 进度显示
```

### 1.2 模块职责说明

#### **core（核心业务逻辑层）**
- **checker.py**: 主检查引擎，协调整个检查流程
  - 职责：流程编排、模块协调、错误处理
  - 依赖：config, data, path, analysis, storage

- **comparator.py**: 文件对比器，执行高性能集合运算
  - 职责：基线与待检查文件列表的Set运算
  - 关键实现：使用Set数据结构，O(n)复杂度

- **result_builder.py**: 结果构建器
  - 职责：构建结构化的检查结果对象
  - 输出：统计信息、详细列表、状态分类

- **task_executor.py**: 任务执行器
  - 职责：处理多对多工程映射关系
  - 关键实现：并行执行、数据预加载、智能调度

#### **config（配置管理层）**
- **loader.py**: 从数据库/文件加载配置
- **models.py**: 配置数据模型（Pydantic）
  - TaskConfig: 任务配置
  - ProjectConfig: 工程配置
  - ShieldConfig: 屏蔽配置
  - PathMappingConfig: 路径映射配置
  - PathPrefixConfig: 路径前缀配置

- **validator.py**: 配置验证，确保数据完整性
- **cache.py**: 配置缓存，避免重复加载

#### **data（数据获取层）**
- **adapters/**: 工程适配器（核心设计）
  - **base.py**: 工程适配器抽象基类
    - 定义统一接口：fetch_task_info(), fetch_file_list()
    - 处理不同类型工程的数据获取差异

  - **api_adapter.py**: API工程适配器
    - 处理通过HTTP API获取数据的工程（公司检查平台）
    - 支持认证、重试、限流

  - **ftp_adapter.py**: FTP工程适配器
    - 处理通过FTP获取离线日志的工程
    - 支持FTP连接池、文件缓存、增量同步

  - **file_adapter.py**: 文件工程适配器
    - 处理本地文件系统的工程（测试/离线工程）
    - 支持本地日志解析

  - **platform_adapters/**: 不同检查平台的专用适配器
    - 每个检查平台可能有特定的API格式和认证方式
    - 通过继承base适配器实现平台特定逻辑

- **factory.py**: 工程工厂
  - 职责：根据工程配置中的type字段创建对应的适配器
  - 关键实现：工厂模式 + 注册机制
  - 支持动态扩展新的工程类型

- **fetcher.py**: 数据获取器
  - 职责：批量获取、并发请求、错误重试
  - 关键实现：使用工程工厂创建适配器，协调多个工程的数据获取

- **models.py**: 数据模型
  - ProjectType: 工程类型枚举（API、FTP、FILE、PLATFORM_A等）
  - FileEntry: 文件条目（路径、状态）
  - TaskInfo: 任务信息（ID、状态、时间、分支）
  - ProjectFileList: 工程文件列表

#### **path（路径处理层）**
- **normalizer.py**: 路径归一化器
  - 职责：统一处理路径前缀，转换为相对路径
  - 关键实现：预编译规则、批量处理

- **matcher.py**: 路径匹配器
  - 职责：屏蔽规则匹配、路径映射规则匹配
  - 支持：精确匹配、正则匹配、通配符匹配

- **trie.py**: 前缀树实现
  - 职责：加速路径前缀匹配
  - 性能：O(L)复杂度（L为路径长度）

- **rules.py**: 路径规则编译器
  - 职责：启动时预编译所有规则（正则、通配符）
  - 避免运行时重复编译

#### **analysis（结果分析层）**
- **ownership.py**: 文件归属分析
  - 职责：批量调用归属接口，获取项目组信息
  - 关键实现：批量API、缓存、限流保护

- **reason_classifier.py**: 缺失原因分类器
  - 职责：分析文件为何缺失（不存在、状态为failed、日志确认）
  - 依赖：cc.json日志解析

- **history_tracker.py**: 历史追踪器
  - 职责：查询数据库历史记录，确定首次发现时间
  - 关键实现：批量查询、时间戳管理

- **async_analyzer.py**: 异步分析任务管理
  - 职责：将耗时的分析任务异步化
  - 关键实现：任务队列、后台worker

#### **storage（持久化层）**
- **database/**: 数据库操作
  - repository.py: 封装CRUD操作
  - models.py: ORM模型（任务汇总、缺失文件详情）
  - 关键实现：批量插入、事务管理

- **report/**: 报告生成
  - generator.py: 生成HTML/JSON报告
  - uploader.py: 上传到对象存储
  - templates/: 报告模板

- **cache/**: 缓存层
  - 支持Redis和内存缓存
  - 缓存文件归属、历史记录等

#### **utils（工具层）**
- **concurrent.py**: 并发处理工具
  - ThreadPoolExecutor/ProcessPoolExecutor封装
  - 超时控制、异常处理

- **batch.py**: 批处理工具
  - chunks生成器
  - 流式处理工具

- **metrics.py**: 指标收集器
  - 记录性能指标、API调用次数、缓存命中率
  - 支持输出到监控系统

- **logger.py**: 日志工具
  - 结构化日志
  - 不同级别的日志输出

- **retry.py**: 重试机制
  - 指数退避
  - 可配置重试次数

#### **cli（命令行接口层）**
- **commands.py**: CLI命令定义
  - check: 执行检查
  - report: 查看报告
  - config: 配置管理

- **output.py**: 输出格式化
  - 表格输出
  - JSON输出
  - 进度条

## 2. 核心对象关系图（文字描述）

### 2.1 配置层对象关系

```
TaskConfig (任务配置)
├── components: List[ComponentInfo]           # 关联的组件信息
├── project_mappings: List[ProjectMapping]    # 工程映射关系
│   ├── target_projects: List[str]           # 待检查工程ID列表
│   └── baseline_projects: List[str]         # 基线工程ID列表
├── shield_configs: List[ShieldConfig]        # 屏蔽配置列表
├── path_mappings: List[PathMappingConfig]    # 路径映射配置列表
└── path_prefixes: List[PathPrefixConfig]     # 路径前缀配置列表

ProjectConfig (工程配置)
├── project_id: str                           # 工程ID
├── project_name: str                         # 工程名称
├── api_endpoint: str                         # API端点
└── credentials: Optional[Dict]               # 认证信息

ShieldConfig (屏蔽配置)
├── id: str                                   # 配置ID
├── pattern: str                              # 路径模式（支持正则/通配符）
├── remark: str                               # 备注信息
└── enabled: bool                             # 是否启用

PathMappingConfig (路径映射配置)
├── id: str                                   # 配置ID
├── source_pattern: str                       # 源路径模式
├── target_pattern: str                       # 目标路径模式
├── remark: str                               # 备注信息
└── enabled: bool                             # 是否启用

PathPrefixConfig (路径前缀配置)
├── project_id: str                           # 工程ID
├── prefix: str                               # 路径前缀
└── trim_prefix: bool                         # 是否移除前缀
```

### 2.2 数据层对象关系

```
TaskInfo (任务信息)
├── task_id: str                              # 任务ID
├── project_id: str                           # 工程ID
├── status: str                               # 任务状态
├── start_time: datetime                      # 开始时间
├── end_time: datetime                        # 结束时间
└── branch_node: str                          # 分支节点信息

FileEntry (文件条目)
├── path: str                                 # 文件路径（原始）
├── normalized_path: str                      # 归一化后的路径
├── status: FileStatus                        # 文件状态（success/failed）
└── metadata: Optional[Dict]                  # 额外元数据

FileStatus (枚举)
├── SUCCESS                                   # 扫描成功
└── FAILED                                    # 扫描失败

ProjectFileList (工程文件列表)
├── project_id: str                           # 工程ID
├── task_info: TaskInfo                       # 任务信息
├── files: Set[str]                           # 文件路径集合（归一化后）
└── raw_files: List[FileEntry]                # 原始文件列表
```

### 2.3 核心业务对象关系

```
CheckTask (检查任务)
├── task_id: str                              # 任务ID
├── target_project: ProjectFileList           # 待检查工程
├── baseline_project: ProjectFileList         # 基线工程
├── config: TaskConfig                        # 任务配置
└── result: CheckResult                       # 检查结果

CheckResult (检查结果)
├── task_id: str                              # 任务ID
├── missing_files: List[MissingFile]          # 缺失文件列表
├── statistics: ResultStatistics              # 统计信息
├── created_at: datetime                      # 创建时间
└── report_url: Optional[str]                 # 报告链接

MissingFile (缺失文件)
├── path: str                                 # 文件路径
├── status: MissingStatus                     # 状态（missed/shielded/remapped）
├── shielded_by: Optional[str]                # 屏蔽配置ID
├── shielded_remark: Optional[str]            # 屏蔽备注
├── remapped_by: Optional[str]                # 映射配置ID
├── remapped_remark: Optional[str]            # 映射备注
├── remapped_to: Optional[str]                # 映射后路径
├── ownership: Optional[str]                  # 归属项目组
├── miss_reason: Optional[MissReason]         # 缺失原因
└── first_detected_at: Optional[datetime]     # 首次发现时间

MissingStatus (枚举)
├── MISSED                                    # 真正缺失
├── SHIELDED                                  # 被屏蔽
└── REMAPPED                                  # 已映射

MissReason (枚举)
├── NOT_EXISTS                                # 待检查列表中不存在
├── SCAN_FAILED                               # 待检查列表中存在但状态为failed
└── LOG_CONFIRMED                             # 通过cc.json日志确认

ResultStatistics (统计信息)
├── total_baseline_files: int                 # 基线文件总数
├── total_target_files: int                   # 待检查文件总数
├── missed_count: int                         # 缺失文件数
├── shielded_count: int                       # 屏蔽文件数
├── remapped_count: int                       # 映射文件数
└── processing_time_sec: float                # 处理耗时
```

### 2.4 路径处理对象关系

```
PathNormalizer (路径归一化器)
├── prefix_rules: List[CompiledPrefixRule]    # 已编译的前缀规则
└── normalize(path: str) -> str               # 归一化方法

PathMatcher (路径匹配器)
├── shield_trie: PathTrie                     # 屏蔽规则前缀树
├── mapping_trie: PathTrie                    # 映射规则前缀树
├── regex_matchers: List[CompiledRegex]       # 正则匹配器
├── match_shield(path: str) -> Optional[ShieldConfig]
└── match_mapping(path: str) -> Optional[PathMappingConfig]

PathTrie (前缀树)
├── root: TrieNode                            # 根节点
├── insert(path: str, value: Any)            # 插入路径
└── search(path: str) -> Optional[Any]       # 搜索路径

CompiledRule (编译后的规则)
├── rule_id: str                              # 规则ID
├── pattern: str                              # 原始模式
├── compiled: Union[re.Pattern, str]          # 编译后的对象
└── metadata: Dict                            # 元数据（备注等）
```

## 3. 数据流转路径

### 3.1 主流程数据流

```
[用户触发]
    ↓
[1. 配置加载阶段]
    TaskConfig ← ConfigLoader.load(task_id)
    ↓ (包含所有配置信息)
    PathNormalizer.init(path_prefixes)      # 初始化路径归一化器
    PathMatcher.init(shields, mappings)      # 初始化路径匹配器
    ↓
[2. 数据获取阶段] (并行)
    ├─ DataFetcher.fetch_target_projects()
    │   ↓ (批量API请求)
    │   └─ List[ProjectFileList]
    │
    └─ DataFetcher.fetch_baseline_projects()
        ↓ (批量API请求)
        └─ List[ProjectFileList]
    ↓
[3. 路径归一化阶段]
    target_files: List[FileEntry]
        ↓ (批量处理)
        PathNormalizer.normalize_batch()
        ↓
    target_normalized: Set[str]             # 归一化后的路径集合

    baseline_files: List[FileEntry]
        ↓ (批量处理)
        PathNormalizer.normalize_batch()
        ↓
    baseline_normalized: Set[str]           # 归一化后的路径集合
    ↓
[4. 核心对比阶段]
    Comparator.compare(baseline_normalized, target_normalized)
        ↓ (Set运算: O(n))
        initial_missing: Set[str] = baseline - target
    ↓
[5. 规则应用阶段]
    for each file in initial_missing:
        ↓
        shield_result = PathMatcher.match_shield(file)
        ↓
        if shield_result:
            MissingFile(status=SHIELDED, shielded_by=shield_result.id)
        else:
            mapping_result = PathMatcher.match_mapping(file)
            ↓
            if mapping_result:
                remapped_path = apply_mapping(file, mapping_result)
                ↓
                if remapped_path in target_normalized:
                    MissingFile(status=REMAPPED, remapped_to=remapped_path)
                else:
                    MissingFile(status=MISSED)
            else:
                MissingFile(status=MISSED)
    ↓
    List[MissingFile]                       # 带状态的缺失文件列表
    ↓
[6. 结果构建阶段]
    ResultBuilder.build(missing_files)
        ↓
        CheckResult(
            missing_files=missing_files,
            statistics=calculate_statistics(missing_files)
        )
    ↓
[7. 异步分析阶段] (可选，不阻塞主流程)
    AsyncAnalyzer.enqueue(missing_files)
        ↓ (后台任务)
        ├─ OwnershipAnalyzer.batch_analyze(files)      # 批量归属分析
        ├─ ReasonClassifier.classify(files)             # 原因分类
        └─ HistoryTracker.track(files)                  # 历史追踪
        ↓
        更新 missing_files 的额外字段
    ↓
[8. 持久化阶段]
    ├─ ReportGenerator.generate(result)
    │   ↓
    │   report_html = render_template(result)
    │   ↓
    │   report_url = Uploader.upload(report_html)
    │
    └─ DatabaseRepository.save(result)
        ↓ (批量插入)
        ├─ save_task_summary(task_id, statistics, report_url)
        └─ batch_save_missing_files(missing_files)
    ↓
[完成]
    返回 CheckResult
```

### 3.2 多对多关系处理流程

```
TaskConfig (3个待检查工程 × 2个基线工程)
    ↓
TaskExecutor.execute_all()
    ↓
[预加载阶段] (一次性加载，避免重复)
    all_targets = {
        "target1": ProjectFileList(...),
        "target2": ProjectFileList(...),
        "target3": ProjectFileList(...)
    }
    all_baselines = {
        "baseline1": ProjectFileList(...),
        "baseline2": ProjectFileList(...)
    }
    ↓
[组合生成]
    combinations = [
        (target1, baseline1),
        (target1, baseline2),
        (target2, baseline1),
        (target2, baseline2),
        (target3, baseline1),
        (target3, baseline2)
    ]  # 6个组合
    ↓
[并行检查]
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(check_combination, target, baseline, config)
            for target, baseline in combinations
        ]
        ↓
        results: List[CheckResult] = [f.result() for f in futures]
    ↓
[结果汇总]
    aggregated_result = aggregate_results(results)
        ↓
        合并所有缺失文件（去重）
        汇总统计信息
        ↓
    FinalResult
```

### 3.3 缓存数据流

```
[首次请求]
    need_data(project_id, task_id)
        ↓
        cache_key = f"project:{project_id}:task:{task_id}"
        ↓
        cached = Cache.get(cache_key)
        ↓
        if cached is None:
            data = API.fetch(project_id, task_id)    # 实际请求
            ↓
            Cache.set(cache_key, data, ttl=3600)     # 缓存1小时
            ↓
            return data
        else:
            return cached                             # 缓存命中

[后续请求]
    need_data(project_id, task_id)
        ↓
        直接从缓存返回 (速度提升10-100倍)
```

## 4. 扩展点设计

### 4.1 数据提供者扩展点

**接口定义**:
```python
class DataProvider(ABC):
    """数据提供者抽象基类"""

    @abstractmethod
    def fetch_task_info(self, project_id: str) -> TaskInfo:
        """获取项目最新任务信息"""
        pass

    @abstractmethod
    def fetch_file_list(self, project_id: str, task_id: str) -> List[FileEntry]:
        """获取任务的文件列表"""
        pass

    @abstractmethod
    def supports_batch(self) -> bool:
        """是否支持批量获取"""
        pass

    @abstractmethod
    def fetch_batch(self, requests: List[FetchRequest]) -> Dict[str, Any]:
        """批量获取数据"""
        pass
```

**扩展场景**:
- APIDataProvider: 从HTTP API获取数据
- DatabaseDataProvider: 从数据库直接查询
- FileDataProvider: 从本地文件读取（用于测试）
- MockDataProvider: 模拟数据（用于单元测试）

**使用方式**:
```python
# 配置中指定数据提供者类型
config = TaskConfig(
    data_provider_type="api",  # 或 "database", "file", "mock"
    data_provider_config={
        "endpoint": "https://api.example.com",
        "auth_token": "xxx"
    }
)

# 运行时动态创建
provider = DataProviderFactory.create(config)
```

### 4.2 路径匹配策略扩展点

**接口定义**:
```python
class PathMatchStrategy(ABC):
    """路径匹配策略接口"""

    @abstractmethod
    def compile(self, pattern: str) -> Any:
        """编译匹配模式"""
        pass

    @abstractmethod
    def match(self, path: str, compiled_pattern: Any) -> bool:
        """判断路径是否匹配"""
        pass

    @abstractmethod
    def transform(self, path: str, pattern: str, target: str) -> str:
        """路径转换（用于映射）"""
        pass
```

**内置策略**:
- ExactMatchStrategy: 精确匹配
- RegexMatchStrategy: 正则表达式匹配
- GlobMatchStrategy: 通配符匹配（*, **, ?）
- PrefixMatchStrategy: 前缀匹配（使用Trie树）

**扩展场景**:
- FuzzyMatchStrategy: 模糊匹配
- SemanticMatchStrategy: 语义匹配（基于相似度）

**使用方式**:
```python
# 在配置中指定匹配策略
shield_config = ShieldConfig(
    pattern="/src/**/*.test.js",
    strategy="glob"  # 或 "regex", "exact", "prefix"
)

# 运行时应用
matcher = PathMatcher(strategies={
    "glob": GlobMatchStrategy(),
    "regex": RegexMatchStrategy(),
    "exact": ExactMatchStrategy()
})
```

### 4.3 结果分析器扩展点

**接口定义**:
```python
class ResultAnalyzer(ABC):
    """结果分析器接口"""

    @abstractmethod
    def analyze(self, missing_files: List[MissingFile], context: AnalysisContext) -> None:
        """分析缺失文件，更新字段"""
        pass

    @abstractmethod
    def priority(self) -> int:
        """分析优先级（数字越小越优先）"""
        pass

    @abstractmethod
    def is_async(self) -> bool:
        """是否可以异步执行"""
        pass
```

**内置分析器**:
- OwnershipAnalyzer: 归属分析（可异步）
- ReasonClassifier: 原因分类（可异步）
- HistoryTracker: 历史追踪（可异步）
- SeverityScorer: 严重程度评分（可扩展）

**扩展场景**:
- CostEstimator: 估算修复成本
- RiskAnalyzer: 风险分析
- TrendAnalyzer: 趋势分析（历史数据对比）

**使用方式**:
```python
# 注册分析器
analysis_pipeline = AnalysisPipeline()
analysis_pipeline.register(OwnershipAnalyzer())
analysis_pipeline.register(ReasonClassifier())
analysis_pipeline.register(CustomAnalyzer())  # 自定义分析器

# 执行分析
analysis_pipeline.run(missing_files, context)
```

### 4.4 报告生成器扩展点

**接口定义**:
```python
class ReportGenerator(ABC):
    """报告生成器接口"""

    @abstractmethod
    def generate(self, result: CheckResult, options: ReportOptions) -> Report:
        """生成报告"""
        pass

    @abstractmethod
    def supported_formats(self) -> List[str]:
        """支持的格式"""
        pass
```

**内置生成器**:
- HTMLReportGenerator: 生成HTML报告（可视化）
- JSONReportGenerator: 生成JSON报告（API集成）
- CSVReportGenerator: 生成CSV报告（Excel导入）
- MarkdownReportGenerator: 生成Markdown报告（文档）

**扩展场景**:
- PDFReportGenerator: 生成PDF报告
- ExcelReportGenerator: 生成Excel报告（带图表）
- SlackReportGenerator: 发送到Slack
- EmailReportGenerator: 发送邮件报告

**使用方式**:
```python
# 配置多种报告格式
report_config = ReportConfig(
    formats=["html", "json", "csv"],
    templates={
        "html": "templates/detailed.html",
        "json": None  # 使用默认
    }
)

# 生成报告
for format in report_config.formats:
    generator = ReportGeneratorFactory.create(format)
    report = generator.generate(result, options)
    uploader.upload(report, format)
```

### 4.5 缓存策略扩展点

**接口定义**:
```python
class CacheBackend(ABC):
    """缓存后端接口"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存"""
        pass

    @abstractmethod
    def clear(self, pattern: str = "*") -> None:
        """清空缓存"""
        pass
```

**内置后端**:
- MemoryCacheBackend: 内存缓存（单机）
- RedisCacheBackend: Redis缓存（分布式）
- FileCacheBackend: 文件缓存（持久化）
- NullCacheBackend: 空缓存（禁用缓存）

**扩展场景**:
- MemcachedCacheBackend: Memcached缓存
- DynamoDBCacheBackend: DynamoDB缓存
- TieredCacheBackend: 多级缓存（L1内存+L2 Redis）

**使用方式**:
```python
# 配置缓存策略
cache_config = CacheConfig(
    backend="redis",
    config={
        "host": "localhost",
        "port": 6379,
        "db": 0
    },
    ttl=3600,
    key_prefix="missing_file_check:"
)

# 运行时切换
cache = CacheFactory.create(cache_config)
```

### 4.6 存储后端扩展点

**接口定义**:
```python
class StorageRepository(ABC):
    """存储仓库接口"""

    @abstractmethod
    def save_task_summary(self, summary: TaskSummary) -> str:
        """保存任务汇总"""
        pass

    @abstractmethod
    def save_missing_files(self, files: List[MissingFile]) -> None:
        """批量保存缺失文件"""
        pass

    @abstractmethod
    def query_history(self, file_paths: List[str]) -> Dict[str, datetime]:
        """查询历史首次发现时间"""
        pass
```

**内置后端**:
- PostgreSQLRepository: PostgreSQL存储
- MySQLRepository: MySQL存储
- SQLiteRepository: SQLite存储（测试/小规模）
- MongoDBRepository: MongoDB存储（文档型）

**扩展场景**:
- ElasticsearchRepository: ES存储（支持全文搜索）
- ClickHouseRepository: ClickHouse存储（大数据分析）
- FileRepository: 文件存储（JSON/CSV）

### 4.7 插件系统

**插件接口**:
```python
class Plugin(ABC):
    """插件基类"""

    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @abstractmethod
    def on_init(self, context: PluginContext) -> None:
        """初始化时调用"""
        pass

    @abstractmethod
    def on_before_check(self, task: CheckTask) -> None:
        """检查前钩子"""
        pass

    @abstractmethod
    def on_after_check(self, result: CheckResult) -> None:
        """检查后钩子"""
        pass

    @abstractmethod
    def on_error(self, error: Exception) -> None:
        """错误处理钩子"""
        pass
```

**插件示例**:
- MetricsPlugin: 收集指标发送到监控系统
- NotificationPlugin: 发送通知（邮件、Slack、钉钉）
- AuditPlugin: 审计日志记录
- RateLimitPlugin: 限流保护
- CircuitBreakerPlugin: 熔断保护

**使用方式**:
```python
# 注册插件
plugin_manager = PluginManager()
plugin_manager.register(MetricsPlugin(config))
plugin_manager.register(NotificationPlugin(config))

# 执行时自动调用钩子
checker = Checker(config, plugin_manager=plugin_manager)
result = checker.check()  # 插件钩子自动执行
```

## 5. 关键设计决策

### 5.1 性能优化设计
- ✅ 使用Set而非List进行文件对比
- ✅ 使用Trie树加速路径匹配
- ✅ 批量API调用减少网络开销
- ✅ 并行处理多对多关系
- ✅ 异步执行耗时分析任务

### 5.2 可扩展性设计
- ✅ 基于接口的抽象（数据提供者、匹配策略、分析器等）
- ✅ 插件系统支持自定义扩展
- ✅ 策略模式支持多种实现
- ✅ 工厂模式支持运行时动态创建

### 5.3 可靠性设计
- ✅ 重试机制处理临时失败
- ✅ 熔断保护避免雪崩
- ✅ 事务管理保证数据一致性
- ✅ 详细日志便于问题排查

### 5.4 可测试性设计
- ✅ 依赖注入便于mock
- ✅ Mock数据提供者支持单元测试
- ✅ 清晰的模块边界便于测试
- ✅ 指标收集便于性能测试

## 6. 技术栈建议

### 6.1 核心依赖
- **Pydantic**: 数据验证和配置管理
- **SQLAlchemy**: ORM和数据库操作
- **Redis-py**: Redis缓存客户端
- **aiohttp**: 异步HTTP客户端
- **Click**: CLI框架

### 6.2 可选依赖
- **Celery**: 异步任务队列
- **Jinja2**: 报告模板引擎
- **pandas**: 数据处理（如需要）
- **prometheus_client**: 指标采集

### 6.3 开发工具
- **pytest**: 单元测试
- **black**: 代码格式化
- **mypy**: 类型检查
- **ruff**: 代码检查

---

**文档版本**: v1.0
**创建日期**: 2026-01-26
**最后更新**: 2026-01-26
