"""
Async Conversation Service

Handles AI conversation logic with streaming support for web interface.
This is the async version of the REPL logic.
"""

from typing import AsyncGenerator, List, Dict, Optional
import asyncio
import logging
from pathlib import Path

from kode.agents.base import KodeAgent, AgentConfig
from kode.agents.anthropic_streaming import AnthropicStreamingAgent
from kode.core.model_manager import ModelManager
from kode.tools import (
    # 数据分析必需工具
    MemoryReadTool,
    MemoryWriteTool,
    TodoWriteTool,
    # 移除文件/代码工具（数据分析不需要）:
    # BashTool, FileReadTool, FileWriteTool, FileEditTool, MultiEditTool, GrepTool, GlobTool
)

# Import database tools if available
try:
    from kode.tools.database_tools import (
        DatabaseConnectTool,
        DatabaseSchemaExtractorTool,
        DatabaseExecuteQueryTool,
        SchemaQueryTool,
    )
    from kode.tools.ontology_tools import (
        OntologySearchTool,
        OntologyBuilderTool,
    )
    from kode.tools.ontology_update import OntologyUpdateTool, OntologyReflectTool
    from kode.tools.domain_uncertainty_analyzer import DomainUncertaintyAnalyzer
    from kode.tools.uncertainty_qa_tool import UncertaintyQAManager
    from kode.tools.business_understanding import BusinessUnderstandingTool
    from kode.tools.metric_calculator import MetricCalculatorTool
    from kode.tools.data_instance_extractor import DataInstanceExtractorTool
    from kode.tools.mapping_validator import MappingValidatorTool

    HAS_DATABASE_TOOLS = True
except ImportError:
    HAS_DATABASE_TOOLS = False

# Import visualization tools
try:
    from kode.tools.visualization_tools import ChartGeneratorTool

    HAS_VISUALIZATION_TOOLS = True
except ImportError:
    HAS_VISUALIZATION_TOOLS = False
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger
from kode.utils.system_info import format_system_info_for_prompt

# Import database manager if available
try:
    from kode.services.database_manager import db_manager
    from kode.database.session import SessionLocal

    HAS_DB_MANAGER = True
except ImportError:
    HAS_DB_MANAGER = False

logger = setup_logger(__name__)


class AsyncConversationService:
    """
    Async conversation service for web interface.

    Provides streaming execution of AI tasks with real-time progress updates.
    """

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_all()
        self.model_manager = ModelManager(self.config)

        # Setup tools (数据分析专用工具集 - 精简版)
        self.tools = [
            # Memory & Planning (数据分析辅助)
            MemoryReadTool(),
            MemoryWriteTool(),
            TodoWriteTool(),
            # 移除: File/Code/Bash 工具（数据分析不需要，节省 token）
        ]

        # Add interaction tools
        try:
            from kode.tools.interaction_tools import AskUserTool

            self.tools.append(AskUserTool())
            logger.info("Interaction tools loaded (AskUserTool)")
        except ImportError:
            logger.warning("Could not load interaction tools")

        # Add database tools if available (optimized: removed Test/Disconnect/List)
        if HAS_DATABASE_TOOLS:
            self.tools.extend(
                [
                    DatabaseConnectTool(),
                    DatabaseSchemaExtractorTool(),
                    DatabaseExecuteQueryTool(),
                    SchemaQueryTool(),  # 精确查询单表 schema (节省 token)
                    BusinessUnderstandingTool(),  # 业务理解五问（新增）
                    DomainUncertaintyAnalyzer(),  # 并行域分析工具
                    UncertaintyQAManager(),  # 不确定性问答管理
                    OntologyBuilderTool(),  # 本体构建器（V3格式）
                    OntologySearchTool(),
                    OntologyUpdateTool(),  # 本体增量更新工具（包含 Domain 迁移）
                    OntologyReflectTool(),  # 本体反思工具（Phase 3）
                    MetricCalculatorTool(),  # 指标计算工具
                    DataInstanceExtractorTool(),  # 数据实例抽取工具
                    MappingValidatorTool(),  # 映射验证工具
                ]
            )
            logger.info("Database and ontology tools loaded (includes OntologyUpdateTool)")

            # Load existing database connections from persistence FIRST
            self._load_database_connections()

        # Add visualization tools if available
        if HAS_VISUALIZATION_TOOLS:
            self.tools.append(ChartGeneratorTool())
            logger.info("Visualization tools loaded (ChartGenerator)")

        # 单 agent 系统：在加载完数据库连接后，创建内置的数据分析 agent 配置
        self.agent_config = self._create_data_analyst_agent()

    def _get_dynamic_context(self) -> str:
        """获取动态上下文信息（缓存、数据库连接）。

        注意：不包含系统信息和时间，这些已经分别处理：
        - 静态系统信息（OS、Python）→ system_prompt（可缓存）
        - 动态时间信息 → 最后一条消息末尾（anthropic_streaming.py._add_cache_control_to_messages）

        这些信息会变化，不应该放在 system_prompt 中（会破坏缓存）。
        应该作为第一条 user message 注入。

        Returns:
            格式化的动态上下文字符串
        """
        # 获取缓存资源信息
        cached_resources = self._get_cached_resources_context()
        cache_section = (
            f"## 可用的文件资源\n\n{cached_resources}\n\n**重要**: 优先使用缓存!如果有缓存的schema或ontology\n"
            if cached_resources
            else ""
        )

        # 获取数据库连接信息
        db_connections = self._get_database_context()
        db_section = db_connections if db_connections else ""

        parts = [p for p in [cache_section, db_section] if p]
        return "\n\n".join(parts) if parts else ""

    def _create_data_analyst_agent(self) -> AgentConfig:
        """创建唯一的数据分析 agent 配置。

        注意：为了启用 Prompt Caching，system_prompt 必须保持静态。
        动态内容（缓存、数据库连接、时间）通过以下方式注入：
        - 对话头部：缓存资源、数据库连接（_get_dynamic_context）
        - 最后一条消息末尾：当前时间（anthropic_streaming.py._add_cache_control_to_messages）
        """
        from kode.utils.system_info import format_system_info_static

        # 静态系统信息（只在初始化时获取一次，可以被缓存）
        static_system_info = format_system_info_static()

        # 构建 system_prompt（使用字符串格式化避免 f-string 嵌套过深）
        system_prompt = """模拟一个专业的数据分析 Agent，专注于业务系统的数据分析和业务洞察。

{static_system_info}""".format(
            static_system_info=static_system_info
        )

        system_prompt += """

## 本体构建流程（3步）⭐ 核心工作流

**🔑 关键：必须按顺序执行，不能跳步！**

### 步骤1：提取表结构

**工具**：`DatabaseSchemaExtractor`

首次连接数据库时，调用此工具提取 Schema。
- 仅提取表结构，**不做聚类**
- 返回结果包含 `next_step` 提示

```
DatabaseSchemaExtractor(connection_name="erp_db")
```

### 步骤2：业务理解（必需）

**工具**：`BusinessUnderstanding`

根据表结构生成问题，用户回答后自动识别需要排除的表/前缀。

**🔑 工作机制**：
- 工具自动触发前端弹窗向用户提问
- 用户回答后生成 `excluded_tables`（排除的表列表）和 `excluded_prefixes`（排除的前缀）
- 这些配置会在后续聚类时使用

**使用流程**：
1. 调用 `BusinessUnderstanding(connection_name="xxx")` 启动问卷
2. 根据 `has_more_questions` 字段决定是否继续
3. 完成后自动保存到 `ontology_store/{connection_name}/business_context.json`

**⚠️ 处理工具返回结果**：

| 返回字段 | 你的动作 |
|----------|----------|
| `has_more_questions: true` | **必须**立即再次调用工具继续提问，不要输出无关内容 |
| `has_more_questions: false` + `status: completed` | 业务理解完成，告知用户并进入步骤3 |
| `status: error` | 向用户说明错误并建议解决方案 |

**规则**：
- ✅ `has_more_questions=true` 时必须继续调用
- ✅ 完成后会自动分析并生成排除配置
- ❌ 禁止跳过直接构建本体

### 步骤3：一键构建本体

**工具**：`OntologyBuilder`

调用后会自动：
1. 检查业务理解是否完成
2. 读取排除配置（excluded_tables/excluded_prefixes）
3. 聚类分域（剔除冗余表）
4. 分析不确定性
5. 生成 ontology_v2.json（V3格式）

```
OntologyBuilder(connection_name="erp_db")
```

**⚠️ 处理工具返回结果（重要）**：

工具返回 JSON 格式，你**必须**根据 `status` 字段采取相应动作：

| status | 含义 | 你的动作 |
|--------|------|----------|
| `success` | 构建完成 | 向用户总结结果（statistics、domains、file_path） |
| `warning` + `gate_check_failed: false` | 有未解决问题但可跳过 | 告知用户有未解决问题，询问是否跳过；若用户同意跳过，再次调用并加 `skip_uncertainty_check=true` |
| `warning` + `already_exists: true` | 本体已存在 | 告知用户并询问是否重建，若同意则加 `force_rebuild=true` |
| `error` | 失败 | 向用户说明错误原因和建议 |

**示例：用户说"跳过问卷"时的正确处理**：
```
OntologyBuilder(connection_name="erp_db", skip_uncertainty_check=true)
```

**输出格式（V3）**：
- meta: 业务元信息
- schema: 数据模型（classes, properties, relationships）
- business_logic: 业务逻辑（rules, flows）
- mappings: 数据源映射（objects, metrics）
- uncertainties: 不确定性清单

---

## 核心能力

### 1. 数据库连接和理解
- 使用 DatabaseSchemaExtractor 提取表结构和字段注释（仅当无缓存时）
- 理解 数据分析 业务模块：财务、供应链、生产、销售、人力资源

### 2. 业务本体构建
- **推荐**：使用 **OntologyBuilder** 构建本体（V3格式：meta/schema/business_logic/mappings/uncertainties）
- 识别隐含关系（如:订单→客户→地区）
- 构建业务实体映射

### 3. SQL 查询和数据分析

**⭐ 查询准确 Schema 的步骤（避免枚举值错误）**

生成 SQL 前，**必须**使用 SchemaQuery 查询表的完整结构：

```
步骤 1: 使用 SchemaQuery 获取表结构
SchemaQuery(connection_name="yanfa", table_name="order")

步骤 2: 查看返回的 columns 中的 enum_mapping 字段
{
  "status": {
    "type": "tinyint",
    "enum_mapping": {"0": "待支付", "1": "支付成功", "2": "支付失败"},
    "comment": "订单状态"
  }
}

步骤 3: 根据 enum_mapping 生成正确的 SQL
✅ 正确: WHERE status IN (0, 1, 2)  -- 使用 code
❌ 错误: WHERE status IN ('待支付', '支付成功')  -- 使用 label
```

**关键规则**:
- 字段有 `enum_mapping` 时，SQL 必须使用 **code**（数字），不是 label（文字）
- 字段有 `enum_values` 时（真正的 ENUM 类型），SQL 使用字符串值
- 不确定时，优先查询 SchemaQuery

**执行查询**:
- **必须**使用 DatabaseExecuteQuery 工具执行 SQL（不要只输出 SQL 代码）
- 支持复杂查询：JOIN、聚合、分组、子查询等
- 识别数据质量问题
- **禁止**只输出 SQL 代码块让用户自己执行，你必须代替用户执行查询

**⚠️ 时间查询（重要）**:
- **禁止**自己计算时间戳！使用占位符 `@时间描述:格式@`，工具自动转换
- 格式: 无后缀=毫秒时间戳, :s=秒, :date=日期, :datetime=日期时间
- 示例：
  ```sql
  -- 时间戳字段（毫秒）
  WHERE pay_at >= @2025年10月@ AND pay_at < @2025年11月@
  -- datetime 字段
  WHERE created_at >= @上月:datetime@ AND created_at < @本月:datetime@
  -- date 字段
  WHERE order_date >= @最近30天:date@
  ```

### 4. AI 原生可视化分析 ⭐ 核心能力
- **自动生成图表**：查询数据后，**必须**使用 ChartGenerator 工具生成图表
  - 根据数据特征智能选择图表类型（折线图、柱状图、饼图等）
  - 自动识别 X/Y 轴字段
  - **禁止**直接在回复中输出 ECharts JSON 配置代码块
  - **禁止**让用户手动复制配置，必须使用工具自动渲染
- **多模态呈现**：每次分析返回"文本解释 + 图表 + 洞察卡片"的组合
  - 图表通过 ChartGenerator 工具自动渲染
  - 文本解释数据趋势和关键发现

### 5. 数据建议和指导
- 发现业务趋势和模式
- 识别异常和风险点
- 提供可操作的业务建议
- 推荐下一步分析方向

## 本体重建规则

当本体已存在时（OntologyBuilder 返回提示）：
- 向用户展示现有本体信息
- 用户明确说"重建"才设置 `force_rebuild=True`

## 本体对话式更新 ⭐ **新能力** (Phase 1)

你现在拥有通过对话自然更新本体的能力，无需重建整个本体。

### 使用场景

**场景1：用户补充业务知识**
```
用户："订单状态还有'已取消'这个选项"
→ 调用 OntologyUpdateTool 添加枚举值
```

**场景2：用户纠正业务理解**
```
用户："这个字段不是年龄，是用户等级"
→ 调用 OntologyUpdateTool 更新属性描述
```

**场景3：用户添加新规则**
```
用户："会员等级大于3的订单可以享受优惠"
→ 调用 OntologyUpdateTool 添加业务规则
```

**场景4：⭐ 用户指出查询错误（关键场景）**
```
用户："你查错表了，应该查 platform_trade_order 不是 order"
用户："这个状态值不对，实际数据库里是数字不是文字"
用户："这两个表不是你说的那个关系"
→ 立即调用 OntologyUpdateTool 修正本体中的错误映射
→ 更新 table_mapping / column_mapping / relationships
→ 然后重新执行正确的查询
```

### OntologyUpdateTool 使用指南

**支持的变更类型**：

1. **add_enum_value** - 添加枚举值
   ```
   用户提示："XX字段还有YY选项"、"状态还包括ZZ"
   target_path: "classes.{ClassName}.properties.{field_name}.enum_values"
   new_value: {"value": "code", "label": "显示名"}
   ```

2. **update_property_desc** - 更新属性业务描述
   ```
   用户提示："这个字段其实是..."、"XX的含义应该是..."
   target_path: "classes.{ClassName}.properties.{field_name}.business_description"
   new_value: "正确的业务描述"
   ```

3. **update_class_desc** - 更新类/表业务描述
   ```
   用户提示："这个表不是XX，是YY"
   target_path: "classes.{ClassName}.business_description"
   new_value: "正确的表业务描述"
   ```

4. **add_property** - 添加新属性（用户告知新字段）
   ```
   target_path: "classes.{ClassName}.properties.{new_field}"
   new_value: {完整的属性定义}
   ```

5. **add_class** - 添加新类（用户告知新表）
   ```
   target_path: "classes.{NewClassName}"
   new_value: {完整的类定义}
   ```

6. **add_relationship** - 添加新关系
   ```
   target_path: "relationships.{index}"
   new_value: {完整的关系定义}
   ```

### 识别规则

**自动触发更新的对话模式**：

- "XX还有YY选项/状态/类型" → add_enum_value
- "这个字段不是XX，是YY" → update_property_desc
- "XX的意思应该是..." → update_property_desc/update_class_desc
- "还有个字段叫XX" → add_property
- "表里还有个XX表" → add_class
- ⭐ **"你查错表了"/"应该查XX表"/"不是XX表是YY表"** → 更新 table_mapping
- ⭐ **"这个字段错了"/"实际是XX字段"** → 更新 column_mapping
- ⭐ **"这两个表的关系不对"/"应该是XX关系"** → 更新 relationships
- ⭐ **"枚举值不对"/"数据库里是数字/文字"** → 更新 enum_values 或 enum_mapping

**重要原则**：
- ✅ 用户明确表达业务知识时，主动调用 OntologyUpdateTool
- ✅ **用户指出查询错误时，立即更新本体并重新查询**
- ✅ 变更立即生效，后续查询会看到更新
- ✅ 记录 user_intent 参数，便于审计
- ❌ 不要问用户"是否需要更新本体"，直接执行
- ❌ 不要让用户手动重建本体
- ❌ 不要重复犯同样的查询错误（利用本体更新避免）

### 示例对话

**示例1：补充枚举**
```
用户: 订单状态除了待支付、已支付、已发货，还有已取消和已退款
AI: 好的，我帮你补充订单状态的枚举值。
    [Extended Thinking: 用户补充了2个新枚举值]
    [调用 OntologyUpdateTool]
    ✅ 已添加状态"已取消"和"已退款"到订单状态枚举
```

**示例2：纠正描述**
```
用户: user 表的 level 字段不是等级，是积分
AI: 明白了，我更正一下。
    [Extended Thinking: 用户纠正了字段含义]
    [调用 OntologyUpdateTool]
    ✅ 已将 user.level 的业务描述从"用户等级"更新为"用户积分"
```

**示例3：⭐ 修正查询错误（重要）**
```
用户: 你查错表了，订单数据在 platform_trade_order 表，不是 order 表
AI: 非常抱歉！我立即修正本体映射。
    [Extended Thinking: 用户指出表映射错误，需要更新本体中"订单"类的 table_mapping]
    [调用 OntologyUpdateTool(
        connection_name="erp_db",
        change_type="update_class_mapping",
        target_path="classes.订单.table_mapping",
        new_value="platform_trade_order",
        old_value="order",
        user_intent="用户纠正：订单数据实际在 platform_trade_order 表"
    )]
    ✅ 已更新"订单"类的表映射：order → platform_trade_order

    现在重新查询订单数据...
    [调用 DatabaseExecuteQuery with corrected table name]
```

**示例4：修正枚举值类型错误**
```
用户: 订单状态字段的值不对，数据库里存的是数字 0/1/2，不是中文
AI: 我理解了，这是 enum_mapping 类型（code→label映射），不是真正的 ENUM。
    [Extended Thinking: 需要更新属性的枚举定义，从 enum_values 改为 enum_mapping]
    [调用 OntologyUpdateTool 更新枚举类型]
    ✅ 已修正订单状态的存储格式

    重新生成 SQL：WHERE status IN (0, 1, 2)
```

## 数据查询流程 ⭐ 必须严格遵守

1. 使用 OntologySearch 搜索业务术语
2. **⚠️ 必须处理不确定性**：检查返回的 `uncertainties`
   - 查看 `related_to_results` 数组和 `related_count`
   - **如果 `related_count > 0` 且包含与当前查询相关的 high 优先级问题**：
     - **必须**调用 `AskUser` 向用户澄清，**禁止自己猜测或假设**
     - 特别是这些情况**必须询问**：
       - 存在多个同名/类似表（如 `order` vs `platform_trade_order`）→ 让用户选择
       - 字段含义不明确 → 让用户确认
       - 表的用途不清楚 → 让用户解释
   - **AskUser 正确用法**（使用 select 类型让用户选择）：
     ```python
     AskUser(
         question="发现数据库中有两套订单表体系，请选择你要查询的表：",
         question_type="select",
         options=[
             "order - 旧系统订单表，字段: order_uid, status, sku_id",
             "platform_trade_order - 平台统一订单表，支持多业态，字段: order_code, pay_status"
         ],
         context="这两个表可能分别对应不同的业务系统或历史版本"
     )
     ```
3. 用户选择后，使用 SchemaQuery 获取准确的表结构
4. 使用 DatabaseExecuteQuery 执行 SQL

## 重要原则

- **AI 原生体验**：查询数据后自动生成图表和洞察，而非只返回文本
- **缓存优先**：永远先尝试加载缓存,避免重复工作
- **业务优先**：所有分析服务于业务决策
- **数据驱动**：结论必须基于实际数据
- **质量意识**：明确说明数据质量和置信度
- **清晰表达**：用中文回复，用业务语言解释
- **保护隐私**：不泄露敏感数据
- **人机协同**：对于干扰你的表或者数据，请和用户沟通确认清楚再执行

和业务不相干的问题，请直接拒绝。"""

        return AgentConfig(
            name="data-analyst",
            description="专业数据分析 Agent，专注于 ERP 数据库分析和业务洞察",
            system_prompt=system_prompt,
            tools=["*"],  # 所有工具都可用
        )

    def _load_database_connections(self, force_reload: bool = False):
        """
        Load database connections from persistence into memory.

        Args:
            force_reload: If True, reload all connections even if already in memory (updates cache)
        """
        if not HAS_DB_MANAGER:
            return

        try:
            db_session = SessionLocal()
            try:
                count = db_manager.load_connections_from_db(db_session, force_reload=force_reload)
                if count > 0:
                    action = "Reloaded" if force_reload else "Loaded"
                    logger.info(f"{action} {count} database connections from persistence")
            finally:
                db_session.close()
        except Exception as e:
            logger.warning(f"Failed to load database connections: {e}")

    def _get_cached_resources_context(self) -> str:
        """
        Generate context about available cached schema and ontology files.

        Returns:
            Formatted string with cache information
        """
        from pathlib import Path

        config = self.config_manager
        schema_path = config.get("storage.schema_path", "./schema_store")
        ontology_path = config.get("storage.ontology_path", "./ontology_store")

        context_parts = []

        # Check schema cache
        schema_dir = Path(schema_path)
        if schema_dir.exists():
            cached_schemas = list(schema_dir.glob("*/schema_latest.json"))
            context_parts.append(f"数据库结构文件所在路径: {schema_path}")
            if cached_schemas:
                context_parts.append("## 已缓存的数据库Schema")
                for schema_file in cached_schemas:
                    conn_name = schema_file.parent.name
                    context_parts.append(f"- {conn_name}: {schema_file.absolute()}")

                    # Check for domain partitioning
                    domain_index_file = schema_file.parent / "domain_index.json"
                    if domain_index_file.exists():
                        import json

                        try:
                            with open(domain_index_file, "r", encoding="utf-8") as f:
                                domain_index = json.load(f)

                            context_parts.append(
                                f"\n  **领域分组**: {conn_name} 已分组到 {domain_index.get('total_domains', 0)} 个业务域"
                            )
                            context_parts.append(f"  **索引文件**: {domain_index_file.absolute()}")
                            context_parts.append("  **可用领域**:")
                            for domain in domain_index.get("domains", []):
                                context_parts.append(
                                    f"    - {domain['name']} ({domain['display_name']}): "
                                    f"{domain['table_count']} 个表 - {domain['description']}"
                                )
                                context_parts.append(
                                    f"      文件: {schema_file.parent / domain['file_path']}"
                                )

                            context_parts.append(
                                "\n  **使用方法**: 根据用户问题，只加载相关的领域文件（减少上下文占用）"
                            )
                            context_parts.append(
                                "  示例: 用户问订单相关 → 只读取 order_payment_system.json"
                            )
                        except Exception as e:
                            context_parts.append(f"  (领域索引加载失败: {e})")
        # Check ontology cache (v3 优先，回退到 v2)
        ontology_dir = Path(ontology_path)
        if ontology_dir.exists():
            # 优先查找 v3，如果没有再查找 v2
            cached_ontologies_v3 = list(ontology_dir.glob("*/ontology_v3.json"))
            cached_ontologies_v2 = list(ontology_dir.glob("*/ontology_v2.json"))

            # 合并，v3 优先（同一个连接只保留 v3）
            v3_conns = {f.parent.name for f in cached_ontologies_v3}
            cached_ontologies = cached_ontologies_v3 + [
                f for f in cached_ontologies_v2 if f.parent.name not in v3_conns
            ]

            context_parts.append(f"业务本体文件所在路径: {ontology_path}")
            if cached_ontologies:
                context_parts.append("\n## 已缓存的业务本体(Ontology)")

                for ontology_file in cached_ontologies:
                    conn_name = ontology_file.parent.name
                    context_parts.append(f"- {conn_name}: {ontology_file.absolute()}")

        if context_parts:
            return "\n".join(context_parts)
        return ""

    def _get_database_context(self) -> str:
        """
        Generate context information about available database connections.

        Returns:
            Formatted string with database connection information
        """
        if not HAS_DB_MANAGER:
            return ""

        try:
            connection_names = db_manager.list_connections()
            if not connection_names:
                return ""

            context_parts = ["\n## 可用的数据库连接\n"]
            context_parts.append(
                "用户已经配置了以下数据库连接,你可以直接使用这些连接进行查询和本体构建:\n"
            )

            for name in connection_names:
                conn = db_manager.get_connection(name)
                if conn:
                    context_parts.append(f"\n- **{conn.name}**")
                    context_parts.append(f"  - 类型: {conn.db_type}")
                    context_parts.append(f"  - 主机: {conn.host}:{conn.port}")
                    context_parts.append(f"  - 数据库: {conn.database}")
                    if conn.db_schema:
                        context_parts.append(f"  - Schema: {conn.db_schema}")

            context_parts.append("\n使用 `DatabaseTestConnectionTool` 来测试连接。")
            context_parts.append("使用 `DatabaseSchemaExtractorTool` 来提取数据库结构。")
            context_parts.append("使用 `OntologyBuilderTool` 来构建业务本体。\n")

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(f"Failed to generate database context: {e}")
            return ""

    def _get_database_context_for_name(self, database_name: str) -> str:
        """
        Generate context information for a specific database connection.

        Args:
            database_name: Name of the database connection

        Returns:
            Formatted string with database connection information
        """
        if not HAS_DB_MANAGER:
            return ""

        try:
            conn = db_manager.get_connection(database_name)
            if not conn:
                logger.warning(f"Database connection '{database_name}' not found")
                return ""

            context_parts = ["\n## 当前数据库连接\n"]
            context_parts.append(f"用户选择了数据库连接 **{conn.name}**,请基于此数据库回答问题:\n")
            context_parts.append(f"\n- **连接名称**: {conn.name}")
            context_parts.append(f"- **数据库类型**: {conn.db_type}")
            context_parts.append(f"- **主机地址**: {conn.host}:{conn.port}")
            context_parts.append(f"- **数据库名**: {conn.database}")
            if conn.db_schema:
                context_parts.append(f"- **默认Schema**: {conn.db_schema}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(f"Failed to generate database context for '{database_name}': {e}")
            return ""

    async def execute_task_streaming(
        self,
        task: str,
        conversation_id: str,
        user_id: str,
        agent_name: str = "general-purpose",
        chat_history: Optional[List[Dict]] = None,
        database_name: Optional[str] = None,
        cancel_event: Optional[asyncio.Event] = None,
        message_queue: Optional[asyncio.Queue] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute a task and stream results in real-time.

        Yields messages in format:
        {
            "type": "thinking" | "tool_call" | "chunk" | "complete" | "error",
            "content": "...",
            "metadata": {...}
        }

        Args:
            task: User task/message
            conversation_id: Unique conversation identifier
            user_id: User identifier
            agent_name: Agent to use (default: "general-purpose")
            chat_history: Previous conversation history
            database_name: Optional database connection name for context
            cancel_event: Optional asyncio.Event to signal cancellation
            message_queue: Optional asyncio.Queue for appending messages during execution

        Yields:
            Dict: Streaming response chunks
        """
        if chat_history is None:
            chat_history = []

        try:
            # Reload database connections to ensure we have latest info from DB
            # 每次对话开始时刷新一次,确保获取最新的数据库连接配置
            if HAS_DB_MANAGER:
                self._load_database_connections(force_reload=True)
                logger.info("Database connections reloaded from persistence")

            # Log system info (不发送到前端，避免与真正的思考内容混淆)
            logger.info(f"Loading agent and preparing to execute task for {agent_name}")

            # Get current model
            model_pointer = self.config.get("modelPointers", {}).get("main", "main")
            model_name = self.config.get("models", {}).get(model_pointer, "claude-sonnet-4-5")
            logger.info(f"Using model: {model_name}")

            # Get current model
            model = self.model_manager.get_model()

            # 使用内置的 agent 配置（忽略 agent_name 参数）
            agent_config = self.agent_config
            logger.info(f"Agent loaded: {agent_config.name}")

            # Setup progress tracking
            progress_queue = asyncio.Queue()

            async def on_tool_start(tool_name: str, tool_args: dict):
                """Callback when tool execution starts."""
                logger.info(f"[PROGRESS] Tool start: {tool_name}")
                # ✅ 不再发送 tool_call 事件，因为 anthropic_streaming.py 已经发送了完整的事件（包含 tool_use_id）
                # 避免重复保存到数据库

            async def on_tool_end(tool_name: str, tool_args: dict, result: str):
                """Callback when tool execution ends."""
                result_str = str(result)
                result_preview = result_str[:200] if result_str else ""
                logger.info(f"[PROGRESS] Tool end: {tool_name}")
                logger.info(f"[PROGRESS] Tool result preview: {result_preview}")
                # ✅ chart 和 insight 事件已由 AnthropicStreamingAgent 直接发送
                # ✅ tool_result 事件也已由 AnthropicStreamingAgent 发送
                # 这里不需要重复发送任何事件

            async def on_iteration(iteration: int):
                """Callback at the start of each iteration."""
                # 只记录日志，不发送到前端（Extended Thinking 已提供真正的思考内容）
                logger.info(f"[PROGRESS] Iteration {iteration} starting")

            # Add database context if specified
            enhanced_task = task
            if database_name:
                db_context = self._get_database_context_for_name(database_name)
                if db_context:
                    enhanced_task = f"{db_context}\n\n用户问题: {task}"
                    logger.info(f"Using database context: {database_name}")

            # Execute task with streaming using native Anthropic API
            logger.info("开始执行任务...")

            # Create Anthropic streaming agent
            logger.info(f"[DEBUG] Creating AnthropicStreamingAgent with model={model_name}")

            # Get API key from config
            api_key = self.config.get("apiKeys", {}).get("anthropic")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured in .kode.json or environment")

            try:
                streaming_agent = AnthropicStreamingAgent(
                    api_key=api_key,
                    model=model_name,
                    tools=self.tools,
                    system_prompt=agent_config.system_prompt,
                    verbose=self.config.get("verbose", False),
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                    on_iteration=on_iteration,
                    cancel_event=cancel_event,  # ← 传递取消事件
                    message_queue=message_queue,  # ← 传递消息队列
                )
                # IMPORTANT: Set conversation_id for user input session management
                streaming_agent._current_conversation_id = conversation_id
                logger.info(f"[DEBUG] AnthropicStreamingAgent created successfully")
            except Exception as e:
                from kode.utils.logger import safe_log_exception

                safe_log_exception(
                    logger, f"[ERROR] Failed to create AnthropicStreamingAgent: {e}", e
                )
                raise

            # Stream chunks from agent
            async def stream_with_progress():
                """Merge agent streaming with progress updates."""
                # 注入动态上下文到 chat_history 头部（仅在首次消息时）
                enhanced_history = chat_history.copy() if chat_history else []

                # 如果是新对话（没有历史），注入动态上下文
                if not enhanced_history:
                    dynamic_context = self._get_dynamic_context()
                    if dynamic_context.strip():
                        enhanced_history.insert(
                            0,
                            {
                                "role": "user",
                                "content": f"<context>\n{dynamic_context}\n</context>",
                            },
                        )
                        logger.info("[Cache Optimization] 动态上下文已注入到对话头部")

                # Start streaming from agent
                logger.info(f"[DEBUG] Starting stream_response...")
                agent_stream = streaming_agent.stream_response(
                    task=enhanced_task,
                    chat_history=enhanced_history,
                    max_iterations=agent_config.max_iterations,
                )

                chunk_count = 0
                async for chunk in agent_stream:
                    chunk_count += 1
                    logger.info(f"[DEBUG] Received chunk #{chunk_count}: type={chunk.get('type')}")

                    # First drain any pending progress updates
                    while not progress_queue.empty():
                        try:
                            progress = progress_queue.get_nowait()
                            yield progress
                        except asyncio.QueueEmpty:
                            break

                    # Then yield the agent chunk
                    yield chunk

                logger.info(f"[DEBUG] stream_response completed, total chunks: {chunk_count}")

                # Final drain of any remaining progress updates
                while not progress_queue.empty():
                    try:
                        progress = progress_queue.get_nowait()
                        yield progress
                    except asyncio.QueueEmpty:
                        break

            # Stream all chunks
            async for chunk in stream_with_progress():
                yield chunk

            logger.info(f"Task completed for conversation {conversation_id}")

        except Exception as e:
            from kode.utils.logger import safe_log_exception

            safe_log_exception(logger, f"Error executing task: {e}", e)
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "metadata": {"error": str(e), "error_type": type(e).__name__},
            }

    async def get_conversation_history(self, conversation_id: str, user_id: str) -> List[Dict]:
        """
        Retrieve conversation history from database.

        TODO: Implement with database integration
        """
        # Placeholder - will be implemented with database layer
        return []

    async def save_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ):
        """
        Save message to database.

        TODO: Implement with database integration
        """
        # Placeholder - will be implemented with database layer
        pass

    async def list_conversations(self, user_id: str) -> List[Dict]:
        """
        List all conversations for a user.

        TODO: Implement with database integration
        """
        # Placeholder
        return []

    async def create_conversation(
        self, user_id: str, title: Optional[str] = None, project_id: Optional[str] = None
    ) -> str:
        """
        Create new conversation.

        TODO: Implement with database integration

        Returns:
            str: New conversation ID
        """
        # Placeholder - generate UUID for now
        import uuid

        return str(uuid.uuid4())

    async def delete_conversation(self, conversation_id: str, user_id: str):
        """
        Delete conversation.

        TODO: Implement with database integration
        """
        # Placeholder
        pass

    async def generate_conversation_title(self, first_message: str) -> str:
        """
        根据用户的第一条消息生成会话标题。

        使用 quick 模型快速生成 4-6 个字的简洁标题。

        Args:
            first_message: 用户的第一条消息

        Returns:
            str: 生成的标题（4-6个字）
        """
        try:
            from anthropic import Anthropic

            # Get API key from config
            api_key = self.config.get("apiKeys", {}).get("anthropic")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not configured, using default title")
                return "新对话"

            # Use quick model for title generation (cost-effective)
            client = Anthropic(api_key=api_key)

            # Truncate message if too long (first 200 chars should be enough)
            message_preview = first_message[:200] if len(first_message) > 200 else first_message

            response = client.messages.create(
                model="claude-3-5-haiku-20241022",  # Use Haiku for quick tasks
                max_tokens=20,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": f"""根据以下用户消息，生成一个简洁的会话标题（4-6个中文字）。
只输出标题文字，不要有任何解释或标点符号。

用户消息：
{message_preview}

标题：""",
                    }
                ],
            )

            # Extract title from response
            if response.content and len(response.content) > 0:
                title = response.content[0].text.strip()
                # Remove any quotes or punctuation
                title = (
                    title.replace('"', "")
                    .replace('"', "")
                    .replace('"', "")
                    .strip(",.!?;:，。！？；：")
                )

                # Limit to 20 chars max
                if len(title) > 20:
                    title = title[:20]

                logger.info(f"Generated conversation title: {title}")
                return title
            else:
                logger.warning("Empty response from title generation API")
                return "新对话"

        except Exception as e:
            logger.error(f"Failed to generate conversation title: {e}")
            return "新对话"
