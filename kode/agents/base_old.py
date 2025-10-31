"""Base classes for Kode agents."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    # Fallback for newer versions of langchain
    from langchain.agents import create_tool_calling_agent
    from langchain_core.agents import AgentExecutor

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


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
        import yaml

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
    A Kode agent that can use tools to accomplish tasks.

    Wraps LangChain's AgentExecutor with Kode-specific functionality.
    """

    def __init__(
        self,
        config: AgentConfig,
        model: Any,
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

        # Create agent
        self.agent = create_tool_calling_agent(self.model, self.tools, self.prompt)

        # Create executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=config.max_iterations,
            max_execution_time=config.max_execution_time,
            handle_parsing_errors=True,
        )

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create chat prompt template for the agent."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", self.config.system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def run(self, task: str, chat_history: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute a task using the agent.

        Args:
            task: Task description
            chat_history: Optional chat history

        Returns:
            Dictionary with 'output' and other execution details
        """
        inputs = {"input": task}
        if chat_history:
            inputs["chat_history"] = chat_history

        return self.executor.invoke(inputs)

    async def arun(
        self, task: str, chat_history: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task asynchronously.

        Args:
            task: Task description
            chat_history: Optional chat history

        Returns:
            Dictionary with 'output' and other execution details
        """
        inputs = {"input": task}
        if chat_history:
            inputs["chat_history"] = chat_history

        return await self.executor.ainvoke(inputs)