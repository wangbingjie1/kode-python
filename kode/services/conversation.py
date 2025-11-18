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
    BashTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    GlobTool,
    GrepTool,
    MemoryReadTool,
    MemoryWriteTool,
    MultiEditTool,
    TodoWriteTool,
)
# Import database tools if available
try:
    from kode.tools.database_tools import (
        DatabaseConnectTool,
        DatabaseSchemaExtractorTool,
        DatabaseExecuteQueryTool,
    )
    from kode.tools.ontology_tools import (
        OntologyBuilderTool,
        OntologySearchTool,
    )
    from kode.tools.domain_uncertainty_analyzer import DomainUncertaintyAnalyzer
    from kode.tools.uncertainty_qa_tool import UncertaintyQAManager
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

        # Setup tools (matching CLI's tool setup)
        self.tools = [
            # File operations
            FileReadTool(),
            FileWriteTool(),
            FileEditTool(),
            MultiEditTool(),
            # Code operations
            BashTool(),
            GrepTool(),
            GlobTool(),
            # Memory
            MemoryReadTool(),
            MemoryWriteTool(),
            # Advanced
            TodoWriteTool(),
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
            self.tools.extend([
                DatabaseConnectTool(),
                DatabaseSchemaExtractorTool(),
                DatabaseExecuteQueryTool(),
                DomainUncertaintyAnalyzer(),  # 并行域分析工具
                UncertaintyQAManager(),  # 不确定性问答管理
                OntologyBuilderTool(),
                OntologySearchTool(),
            ])
            logger.info("Database and ontology tools loaded (with uncertainty Q&A system)")

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
        - 动态时间信息 → 每次迭代尾部（anthropic_streaming.py）

        这些信息会变化，不应该放在 system_prompt 中（会破坏缓存）。
        应该作为第一条 user message 注入。

        Returns:
            格式化的动态上下文字符串
        """
        # 获取缓存资源信息
        cached_resources = self._get_cached_resources_context()
        cache_section = f"## 可用的文件资源\n\n{cached_resources}\n\n**重要**: 优先使用缓存!如果有缓存的schema或ontology\n" if cached_resources else ""

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
        - 每次迭代尾部：当前时间、token 预算（anthropic_streaming.py）
        """
        from kode.utils.system_info import format_system_info_static

        # 静态系统信息（只在初始化时获取一次，可以被缓存）
        static_system_info = format_system_info_static()

        return AgentConfig(
            name="data-analyst",
            # betas=["context-1m-2025-08-07"],
            description="专业数据分析 Agent，专注于 ERP 数据库分析和业务洞察",
            system_prompt=f"""你是一个专业的数据分析 Agent，专注于 ERP 系统的数据分析和业务洞察。

{static_system_info}

## 核心能力

### 1. 数据库连接和理解
- 使用 DatabaseSchemaExtractor 提取表结构和字段注释（仅当无缓存时）
- 理解 数据分析 业务模块：财务、供应链、生产、销售、人力资源

### 2. 业务本体构建
- 使用 OntologyBuilder 将技术表结构转换为业务语义（仅当无缓存时）
- 识别隐含关系（如:订单→客户→地区）
- 构建业务实体映射

### 3. SQL 查询和数据分析
- 使用 DatabaseExecuteQuery 执行 SQL 查询（复杂 JOIN、聚合、分组）
- 计算关键业务指标（KPI）：销售额、库存周转率、客户留存率等
- 识别数据质量问题

### 4. AI 原生可视化分析 ⭐ 核心能力
- **自动生成图表**：查询数据后，使用 ChartGenerator 自动生成图表配置
  - 根据数据特征智能选择图表类型（折线图、柱状图、饼图等）
  - 自动识别 X/Y 轴字段
  - 生成 ECharts 配置 JSON
- **多模态呈现**：每次分析返回"文本解释 + 图表 + 洞察卡片"的组合

### 5. 数据建议和指导
- 发现业务趋势和模式
- 识别异常和风险点
- 提供可操作的业务建议
- 推荐下一步分析方向

## 本体构建工作流流程（首次连接数据库时执行）⭐ 智能简化版

**前提**：Schema 已通过 DatabaseSchemaExtractor 提取并保存

### 🚀 智能检测逻辑（OntologyBuilder 自动执行）

**重要**：直接调用 **OntologyBuilder** 即可，它会自动检测并提示后续步骤。

```
用户: "帮我构建本体"
↓
OntologyBuilder 自动检测：
  1. 检查 domains/*.json 领域文件是否存在
     ├─ 不存在 → 返回错误，提示先运行 DatabaseSchemaExtractor
     └─ 存在 → 继续检查 high 问题
  2. 读取各领域文件中的 uncertainties 字段，检查 high 优先级问题状态
     ├─ 有未解决 → 返回错误，提示使用 UncertaintyQAManager
     └─ 全部已解决 → 开始构建本体（自动注入用户确认的业务规则）
```

**✨ 新架构说明**：
- 不确定性数据已分散存储在各领域文件（`domains/{{domain_name}}.json`）的 `uncertainties` 字段中
- 不再需要单独的 `uncertainties.json` 文件
- OntologyBuilder 会自动从领域文件中读取已解决的 high 问题答案，注入到构建 Prompt 中

**你不需要手动判断，OntologyBuilder 会自动提示正确的操作步骤！**

---

### 第1步：检查不确定性状态（自动完成）

- OntologyBuilder 会自动读取所有领域文件中的 `uncertainties` 字段
- 如果有未解决的 high 优先级问题，会提示使用 UncertaintyQAManager

### 第2步：回答高优先级问题（如果有未解决问题）⭐ 关键卡点

**使用 UncertaintyQAManager 工具管理问答流程**：

1. **加载问题列表**：
   ```
   UncertaintyQAManager(connection_name="yanfa", action="load")
   ```
   - 返回所有未解决的 high 优先级问题
   - 每个问题包含唯一 ID、问题描述、上下文、影响等信息

2. **提问并记录回答（两种模式）**：

   **模式A：批量问答（推荐，用户友好）⭐**
   - 当问题数量 >= 5 时，使用批量模式
   - 步骤：
     a) 批量加载问题（支持分组和限制数量）：
        ```
        UncertaintyQAManager(
          connection_name="yanfa",
          action="batch_load",
          group_by="domain",  # 或 "priority"
          limit=10  # 可选，限制问题数量
        )
        ```
     b) **直接告诉用户**："我已经为你准备了批量问答表单，请在界面上填写并提交。提交后我会继续处理。"
        - ⚠️ **不要使用 AskUser 工具**，因为前端会自动渲染表单
        - 等待用户在前端填写表单并提交
     c) 用户提交后，前端会调用 batch_answer API，工具会自动记录所有答案

   **模式B：逐个问答（问题数量 < 5 时使用）**
   - 使用 **AskUser** 工具逐个提问
   - 问题格式：`{{question}}\\n\\n上下文：{{context}}\\n影响：{{impact}}`
   - 获得用户回答后，立即记录：
     ```
     UncertaintyQAManager(
       connection_name="yanfa",
       action="answer",
       uncertainty_id="user_management_platform_user_0",
       answer="用户的回答内容"
     )
     ```

3. **检查进度**：
   ```
   UncertaintyQAManager(connection_name="yanfa", action="status")
   ```
   - 返回剩余未解决的 high 问题数量
   - can_build_ontology: true/false

4. **强制门禁**：
   - **只有当 can_build_ontology=true 时** → 才能调用 OntologyBuilder
   - 否则必须继续提问，直到所有 high 问题解决

### 第3步：构建本体
- 调用 **OntologyBuilder** 将 schema 转换为业务本体
- **重要**：构建时会自动包含所有域的不确定性（包括已解决的）
- 自动保存为 ontology_latest.json

### 第4步：可选 - 处理 medium/low 优先级问题
- 可在后续分析过程中，遇到相关问题时再询问用户
- 使用 **OntologyUncertaintyResolver** 记录答案并更新本体

**强制规则**：
- ❌ **禁止跳过第2步**，high 优先级问题必须全部解决
- ✅ medium/low 问题可以延迟处理
- ✅ 所有不确定性记录在本体中，用于后续分析时参考

## 用户问答工作流流程（强制执行，不可跳过）⭐

### 核心流程（5步法）

1. **验证本体缓存**
   - 如果没有本体文件 → 停止并提示用户先构建本体
   - 找到本体文件 → 继续执行

2. **语义搜索** → 使用 OntologySearch 工具（这一步会自动返回相关的 uncertainties）
   - 从用户问题提取关键业务术语（如"订单"、"用户"、"销售额"）
   - 搜索本体中的 concepts 和 properties
   - **工具会自动返回以下内容**：
     * results.concepts: 相关的业务概念（含 data_source）
     * results.properties: 相关的属性（含 data_source）
     * **uncertainties.related**: 与本次查询相关的不确定性列表 ⭐
     * uncertainties.all_unresolved: 所有未解决的不确定性

3. **分析不确定性（关键步骤！）** ⭐⭐⭐
   - 检查 OntologySearch 返回的 `uncertainties.related` 列表

   - **如果存在已解决的不确定性（status=resolved）**：
     a. **严格遵循用户的回答（answer字段）**
     b. 示例："订单表歧义已解决，用户确认使用 platform_trade_order（order表已废弃）"
     c. **直接应用，无需再次询问用户**
     d. 在生成SQL时遵循这些规则

   - **如果存在未解决的不确定性（status=unresolved）**：
     a. **优先处理 high priority 的不确定性**
     b. **使用 AskUser 工具询问用户**，例如：
        "您提到的'订单'，系统发现有2个订单表（order 和 platform_trade_order），请问您想查询的是哪个订单表？"
     c. 等待用户回答后再继续
     d. 可选：使用 OntologyUncertaintyResolver 工具记录用户的回答

   - **如果没有相关不确定性** → 继续下一步

4. **生成并执行 SQL**
   - 从 OntologySearch 结果获取 data_source（表名、字段名）
   - 从 relationships 获取表关联关系
   - 生成 SQL（必须在注释中标注业务含义）
   - 使用 DatabaseExecuteQuery 执行查询

5. **结果展示（数据溯源）**
   - 格式：数据来自 {{{{business_name_cn}}}} ({{{{technical_name}}}}表)
   - 在回复中包含业务术语的中文名称

**强制规则**：
- ❌ 禁止忽略 uncertainties.related 列表中的 high priority 不确定性
- ✅ **必须**检查并处理相关的不确定性（使用 AskUser 工具）
- ✅ 必须在回复中包含业务术语的中文名称（从本体获取）
- ✅ 必须在 SQL 中注释字段的业务含义

### 示例：处理不确定性的正确流程

**场景**：用户问"查询最近的订单"

```
步骤1: 使用 OntologySearch 搜索"订单"
返回结果:
{{{{
  "results": {{{{
    "concepts": [
      {{{{"technical_name": "order", "business_name_cn": "订单", ...}}}},
      {{{{"technical_name": "platform_trade_order", "business_name_cn": "平台交易订单", ...}}}}
    ]
  }}}},
  "uncertainties": {{{{
    "related": [
      {{{{
        "type": "schema_ambiguity",
        "priority": "high",
        "entity": "order",
        "question": "系统中存在 order 和 platform_trade_order 两个订单表，无法区分用途",
        "status": "unresolved"
      }}}}
    ]
  }}}}
}}}}

步骤2: 发现 high priority 不确定性 → 使用 AskUser 工具
AskUser({{{{
  "question": "您好，系统中发现有两个订单表：\\n1. order（订单表）\\n2. platform_trade_order（平台交易订单表）\\n请问您想查询的是哪个订单表？",
  "context": "...",
  "options": ["order", "platform_trade_order"]
}}}})

步骤3: 等待用户回答 → 假设用户选择 "platform_trade_order"

步骤4: 生成 SQL 并执行
SELECT * FROM platform_trade_order -- 平台交易订单表
ORDER BY create_time DESC
LIMIT 10;

步骤5: 记录用户的回答
OntologyUncertaintyResolver({{{{
  "connection_name": "erp_db",
  "uncertainty_index": 0,
  "resolution": "用户明确表示查询 platform_trade_order 表"
}}}})
```

### 上下文预算主动管理

**监控你的"注意力"**：
- 每次迭代前检查剩余预算百分比（系统会自动注入）
- 剩余 < 30%: 避免读取大文件,优先使用 Grep
- 剩余 < 10%: 立即提醒用户开启新对话


## 重要原则

- **AI 原生体验**：查询数据后自动生成图表和洞察，而非只返回文本
- **缓存优先**：永远先尝试加载缓存,避免重复工作
- **业务优先**：所有分析服务于业务决策
- **数据驱动**：结论必须基于实际数据
- **质量意识**：明确说明数据质量和置信度
- **清晰表达**：用中文回复，用业务语言解释
- **保护隐私**：不泄露敏感数据
- **人机协同**：对于干扰你的表或者数据，请和用户沟通确认清楚再执行
- **上下文意识**：主动管理你的注意力预算，使用glob， Grep先探索，然后使用FileRead读取关键内容

和业务不相干的问题，请直接拒绝。""",
            tools=["*"],  # 所有工具都可用
        )

    def _load_database_connections(self):
        """Load database connections from persistence into memory."""
        if not HAS_DB_MANAGER:
            return

        try:
            db_session = SessionLocal()
            try:
                count = db_manager.load_connections_from_db(db_session)
                if count > 0:
                    logger.info(f"Loaded {count} database connections from persistence")
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
                            with open(domain_index_file, 'r', encoding='utf-8') as f:
                                domain_index = json.load(f)

                            context_parts.append(f"\n  **领域分组**: {conn_name} 已分组到 {domain_index.get('total_domains', 0)} 个业务域")
                            context_parts.append(f"  **索引文件**: {domain_index_file.absolute()}")
                            context_parts.append("  **可用领域**:")
                            for domain in domain_index.get('domains', []):
                                context_parts.append(
                                    f"    - {domain['name']} ({domain['display_name']}): "
                                    f"{domain['table_count']} 个表 - {domain['description']}"
                                )
                                context_parts.append(f"      文件: {schema_file.parent / domain['file_path']}")

                            context_parts.append("\n  **使用方法**: 根据用户问题，只加载相关的领域文件（减少上下文占用）")
                            context_parts.append("  示例: 用户问订单相关 → 只读取 order_payment_system.json")
                        except Exception as e:
                            context_parts.append(f"  (领域索引加载失败: {e})")

                    # Check for uncertainty analysis file
                    uncertainties_file = schema_file.parent / "uncertainties.json"
                    if uncertainties_file.exists():
                        context_parts.append(f"\n  **不确定性分析**: {uncertainties_file.absolute()}")
                        context_parts.append("  包含业务规则不明确、数据不一致、缺失约束等需要与用户确认的问题")
                        context_parts.append("  **使用方法**: 需要深入分析数据问题时，使用 UncertaintyQATool 工具进行问答式诊断")

        # Check ontology cache
        ontology_dir = Path(ontology_path)
        if ontology_dir.exists():
            cached_ontologies = list(ontology_dir.glob("*/ontology_latest.json"))
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
            context_parts.append("用户已经配置了以下数据库连接,你可以直接使用这些连接进行查询和本体构建:\n")

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

        Yields:
            Dict: Streaming response chunks
        """
        if chat_history is None:
            chat_history = []

        try:
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
                logger.warning(f"[CALLBACK] on_tool_start called: {tool_name}")  # Use warning to ensure visibility
                logger.warning(f"[CALLBACK] Tool args: {tool_args}")
                # Send progress update as tool_call event
                await progress_queue.put({
                    "type": "tool_call",
                    "content": f"正在执行工具: {tool_name}",
                    "metadata": {"tool_name": tool_name, "status": "started", "args": tool_args}
                })
                logger.warning(f"[CALLBACK] Queued tool_call event for {tool_name}")

            async def on_tool_end(tool_name: str, tool_args: dict, result: str):
                """Callback when tool execution ends."""
                result_str = str(result)
                result_preview = result_str[:200] if result_str else ""
                logger.info(f"[PROGRESS] Tool end: {tool_name}")
                logger.info(f"[PROGRESS] Tool result preview: {result_preview}")

                # 解析可视化工具结果，发送专门的消息类型
                if tool_name == "ChartGenerator":
                    try:
                        import json
                        chart_result = json.loads(result_str)
                        if chart_result.get("success"):
                            # 发送 chart 类型消息
                            await progress_queue.put({
                                "type": "chart",
                                "content": chart_result.get("config", {}),
                                "metadata": {
                                    "chart_type": chart_result.get("chart_type"),
                                    "data_summary": chart_result.get("data_summary", {})
                                }
                            })
                            logger.info(f"[CHART] Sent chart message for type: {chart_result.get('chart_type')}")
                    except Exception as e:
                        logger.error(f"[CHART] Failed to parse chart result: {e}")

                elif tool_name == "InsightExtractor":
                    try:
                        import json
                        insight_result = json.loads(result_str)
                        if insight_result.get("success"):
                            insights = insight_result.get("insights", [])
                            # 发送 insight 类型消息
                            await progress_queue.put({
                                "type": "insight",
                                "content": insights,
                                "metadata": {
                                    "total_count": insight_result.get("total_count", 0),
                                    "data_summary": insight_result.get("data_summary", {})
                                }
                            })
                            logger.info(f"[INSIGHT] Sent {len(insights)} insights")
                    except Exception as e:
                        logger.error(f"[INSIGHT] Failed to parse insight result: {e}")

                # Send standard tool_result for all tools
                await progress_queue.put({
                    "type": "tool_result",
                    "content": f"工具执行完成: {tool_name}",
                    "metadata": {
                        "tool_name": tool_name,
                        "status": "completed",
                        "tool_args": tool_args,
                        "result": result_str  # Send full result
                    }
                })

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
                )
                # IMPORTANT: Set conversation_id for user input session management
                streaming_agent._current_conversation_id = conversation_id
                logger.info(f"[DEBUG] AnthropicStreamingAgent created successfully")
            except Exception as e:
                from kode.utils.logger import safe_log_exception
                safe_log_exception(logger, f"[ERROR] Failed to create AnthropicStreamingAgent: {e}", e)
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
                        enhanced_history.insert(0, {
                            "role": "user",
                            "content": f"<context>\n{dynamic_context}\n</context>"
                        })
                        logger.info("[Cache Optimization] 动态上下文已注入到对话头部")

                # Start streaming from agent
                logger.info(f"[DEBUG] Starting stream_response...")
                agent_stream = streaming_agent.stream_response(
                    task=enhanced_task,
                    chat_history=enhanced_history,
                    max_iterations=agent_config.max_iterations
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

    async def get_conversation_history(
        self, conversation_id: str, user_id: str
    ) -> List[Dict]:
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
