"""Simplified base classes for Kode agents - compatible with LangChain 1.0+."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool


@dataclass
class AgentConfig:
    """
    Configuration for a Kode agent.

    Loaded from markdown files with YAML frontmatter.
    """

    name: str
    description: str
    system_prompt: str
    tools: List[str] = field(default_factory=lambda: ["*"])
    model: Optional[str] = None
    max_iterations: int = 15
    max_execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_markdown(cls, content: str) -> "AgentConfig":
        """
        Parse agent configuration from markdown file.

        Expected format:
        ---
        name: agent-name
        description: "When to use this agent"
        tools: ["FileRead", "Bash"]  # or "*" for all
        model: model-name  # optional
        ---

        System prompt content here...

        Args:
            content: Markdown file content

        Returns:
            AgentConfig instance
        """
        # Split frontmatter and content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                system_prompt = parts[2].strip()
            else:
                raise ValueError("Invalid markdown format: missing closing ---")
        else:
            raise ValueError("Invalid markdown format: missing frontmatter")

        return cls(
            name=frontmatter.get("name", "unknown"),
            description=frontmatter.get("description", ""),
            system_prompt=system_prompt,
            tools=frontmatter.get("tools", ["*"]),
            model=frontmatter.get("model"),
            max_iterations=frontmatter.get("max_iterations", 15),
            max_execution_time=frontmatter.get("max_execution_time"),
            metadata=frontmatter.get("metadata", {}),
        )


class KodeAgent:
    """
    A simplified Kode agent for direct LLM interaction.

    This is a simplified version that doesn't use AgentExecutor,
    which may not be available in all LangChain versions.
    """

    def __init__(
        self,
        config: AgentConfig,
        model: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
    ):
        """
        Initialize Kode agent.

        Args:
            config: Agent configuration
            model: LangChain chat model
            tools: List of available tools
            verbose: Whether to print verbose output
        """
        self.config = config
        self.model = model
        self.tools = tools
        self.verbose = verbose

        # Create agent prompt
        self.prompt = self._create_prompt()

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create chat prompt template for the agent."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", self.config.system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
            ]
        )

    def run(self, task: str, chat_history: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute a task using the agent (simple version).

        Args:
            task: Task description
            chat_history: Optional chat history

        Returns:
            Dictionary with 'output' and other execution details
        """
        # Format prompt
        messages = self.prompt.format_messages(
            input=task, chat_history=chat_history or []
        )

        # Call model
        response = self.model.invoke(messages)

        # Return result
        return {"output": response.content, "messages": messages, "response": response}

    async def arun(
        self, task: str, chat_history: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task asynchronously (simple version).

        Args:
            task: Task description
            chat_history: Optional chat history

        Returns:
            Dictionary with 'output' and other execution details
        """
        # Format prompt
        messages = self.prompt.format_messages(
            input=task, chat_history=chat_history or []
        )

        # Call model
        response = await self.model.ainvoke(messages)

        # Return result
        return {"output": response.content, "messages": messages, "response": response}
