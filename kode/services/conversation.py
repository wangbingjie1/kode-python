"""
Async Conversation Service

Handles AI conversation logic with streaming support for web interface.
This is the async version of the REPL logic.
"""

from typing import AsyncGenerator, List, Dict, Optional
import asyncio
import logging
from pathlib import Path

from kode.agents.base import KodeAgent
from kode.agents.loader import AgentLoader
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
    URLFetcherTool,
    WebSearchTool,
    NotebookReadTool,
    NotebookEditTool,
    MultiEditTool,
    ThinkTool,
    TodoWriteTool,
    TaskTool,
)
# Import database tools if available
try:
    from kode.tools.database_tools import (
        DatabaseConnectTool,
        DatabaseTestConnectionTool,
        DatabaseSchemaExtractorTool,
        DatabaseListConnectionsTool,
        DatabaseDisconnectTool,
    )
    from kode.tools.ontology_tools import (
        OntologyBuilderTool,
        OntologyStorageTool,
        OntologySearchTool,
    )
    HAS_DATABASE_TOOLS = True
except ImportError:
    HAS_DATABASE_TOOLS = False
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger

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
        self.agent_loader = AgentLoader(project_root=str(Path.cwd()))

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
            # Web
            URLFetcherTool(),
            WebSearchTool(),
            # Notebooks
            NotebookReadTool(),
            NotebookEditTool(),
            # Advanced
            ThinkTool(),
            TodoWriteTool(),
            TaskTool(),
        ]

        # Add database tools if available
        if HAS_DATABASE_TOOLS:
            self.tools.extend([
                DatabaseConnectTool(),
                DatabaseTestConnectionTool(),
                DatabaseSchemaExtractorTool(),
                DatabaseListConnectionsTool(),
                DatabaseDisconnectTool(),
                OntologyBuilderTool(),
                OntologyStorageTool(),
                OntologySearchTool(),
            ])
            logger.info("Database and ontology tools loaded")

            # Load existing database connections from persistence
            self._load_database_connections()

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

            context_parts.append("\n**重要提示**:")
            context_parts.append("1. 使用 `DatabaseTestConnectionTool` 测试连接健康状态")
            context_parts.append("2. 使用 `DatabaseSchemaExtractorTool` 提取完整的数据库结构(表、字段、关系等)")
            context_parts.append("3. 使用 `OntologyBuilderTool` 构建业务本体模型")
            context_parts.append("4. 回答问题时请结合提取的数据库结构信息\n")

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
            # Yield initial thinking status
            yield {
                "type": "thinking",
                "content": "Loading agent and preparing to execute task...",
                "metadata": {"agent": agent_name},
            }

            # Get current model
            model_pointer = self.config.get("modelPointers", {}).get("main", "main")
            model_name = self.config.get("models", {}).get(model_pointer, "claude-sonnet-4-5")

            yield {
                "type": "thinking",
                "content": f"Using model: {model_name}",
                "metadata": {"model": model_name},
            }

            # Get current model
            model = self.model_manager.get_model()

            # Load agent configuration
            agent_config = self.agent_loader.load_agent(agent_name)
            if not agent_config:
                raise ValueError(f"Agent '{agent_name}' not found")

            yield {
                "type": "thinking",
                "content": f"Agent loaded: {agent_config.name}",
                "metadata": {"agent_config": agent_config.name},
            }

            # Track tool calls for streaming
            tool_calls = []

            def on_tool_start(tool_name: str, tool_args: dict):
                """Callback when tool execution starts."""
                tool_calls.append({
                    "name": tool_name,
                    "args": tool_args,
                    "status": "started"
                })

            def on_tool_end(tool_name: str, tool_args: dict, result: str):
                """Callback when tool execution ends."""
                # Find and update the tool call
                for tc in tool_calls:
                    if tc["name"] == tool_name and tc.get("status") == "started":
                        tc["status"] = "completed"
                        tc["result"] = str(result)[:200]  # Truncate
                        break

            # Create agent instance with callbacks
            agent = KodeAgent(
                config=agent_config,
                model=model,
                tools=self.tools,
                verbose=self.config.get("verbose", False),
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
            )

            # Add database context if specified
            enhanced_task = task
            if database_name:
                db_context = self._get_database_context_for_name(database_name)
                if db_context:
                    enhanced_task = f"{db_context}\n\n用户问题: {task}"
                    yield {
                        "type": "thinking",
                        "content": f"Using database context: {database_name}",
                        "metadata": {"database": database_name},
                    }

            # Execute task with streaming
            yield {
                "type": "thinking",
                "content": "Executing task...",
                "metadata": {"status": "executing"},
            }

            # Run agent (async)
            result = await agent.arun(task=enhanced_task, chat_history=chat_history)

            # Send tool calls info
            if result.get("tool_calls"):
                for tool_call in result["tool_calls"]:
                    yield {
                        "type": "tool_call",
                        "content": f"Tool: {tool_call['name']}",
                        "metadata": {
                            "tool_name": tool_call["name"],
                            "tool_args": tool_call.get("args", {}),
                            "result": tool_call.get("result", "")[:200] if "result" in tool_call else None,
                            "error": tool_call.get("error"),
                        },
                    }

            # Send final output
            output = result.get("output", "")

            yield {
                "type": "chunk",
                "content": output,
                "metadata": {
                    "agent": agent_name,
                    "model": model_name,
                    "iterations": result.get("iterations", 0),
                },
            }

            # Convert messages to serializable format
            messages = result.get("messages", [])
            serializable_messages = []
            for msg in messages:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    # LangChain message object
                    msg_dict = {
                        "role": msg.type if hasattr(msg, "type") else "unknown",
                        "content": str(msg.content)
                    }
                    # Add tool_calls if present
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        msg_dict["tool_calls"] = msg.tool_calls
                    serializable_messages.append(msg_dict)
                elif isinstance(msg, dict):
                    # Already a dict
                    serializable_messages.append(msg)

            # Yield completion
            yield {
                "type": "complete",
                "content": output,
                "metadata": {
                    "agent": agent_name,
                    "model": model_name,
                    "conversation_id": conversation_id,
                    "messages": serializable_messages,
                    "tool_calls": result.get("tool_calls", []),
                    "iterations": result.get("iterations", 0),
                },
            }

            logger.info(f"Task completed for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error executing task: {e}", exc_info=True)
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
