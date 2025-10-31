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
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger

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

    async def execute_task_streaming(
        self,
        task: str,
        conversation_id: str,
        user_id: str,
        agent_name: str = "general-purpose",
        chat_history: Optional[List[Dict]] = None,
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

            # Create agent instance
            agent = KodeAgent(
                config=agent_config,
                model=model,
                tools=self.tools,
                verbose=self.config.get("verbose", False),
            )

            # Execute task with streaming
            # Note: Current KodeAgent.arun() returns full response
            # TODO: Implement token-level streaming in future iteration
            yield {
                "type": "thinking",
                "content": "Executing task...",
                "metadata": {"status": "executing"},
            }

            # Run agent (async)
            result = await agent.arun(task=task, chat_history=chat_history)

            # For now, send complete response as single chunk
            # In future, integrate with LangChain streaming callbacks
            output = result.get("output", "")

            yield {
                "type": "chunk",
                "content": output,
                "metadata": {
                    "agent": agent_name,
                    "model": model_name,
                },
            }

            # Convert messages to serializable format
            messages = result.get("messages", [])
            serializable_messages = []
            for msg in messages:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    # LangChain message object
                    serializable_messages.append({
                        "role": msg.type if hasattr(msg, "type") else "unknown",
                        "content": str(msg.content)
                    })
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
