"""Simplified base classes for Kode agents - compatible with LangChain 1.0+."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

import yaml
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
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
    def from_markdown(cls, content: str, config_vars: Optional[Dict[str, Any]] = None) -> "AgentConfig":
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
        Support variable injection: {schema_path}, {ontology_path}, etc.

        Args:
            content: Markdown file content
            config_vars: Configuration variables for injection

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

        # Inject configuration variables into system prompt
        if config_vars:
            system_prompt = cls._inject_variables(system_prompt, config_vars)

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

    @staticmethod
    def _inject_variables(prompt: str, config_vars: Dict[str, Any]) -> str:
        """
        Inject configuration variables into prompt template.

        Supports placeholders like: {schema_path}, {ontology_path}, {connection_name}

        Args:
            prompt: Prompt template with placeholders
            config_vars: Variable values to inject

        Returns:
            Prompt with variables injected
        """
        try:
            return prompt.format(**config_vars)
        except KeyError as e:
            # If a placeholder is not provided, leave it as-is
            import re
            # Replace only available variables
            for key, value in config_vars.items():
                placeholder = "{" + key + "}"
                prompt = prompt.replace(placeholder, str(value))
            return prompt


class KodeAgent:
    """
    A simplified Kode agent with tool calling support.

    Supports tool binding and execution in a multi-turn conversation loop.
    """

    def __init__(
        self,
        config: AgentConfig,
        model: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
        on_tool_start: Optional[Callable] = None,
        on_tool_end: Optional[Callable] = None,
        on_iteration: Optional[Callable] = None,
    ):
        """
        Initialize Kode agent.

        Args:
            config: Agent configuration
            model: LangChain chat model
            tools: List of available tools
            verbose: Whether to print verbose output
            on_tool_start: Callback when tool execution starts
            on_tool_end: Callback when tool execution ends
            on_iteration: Callback at the start of each iteration
        """
        self.config = config
        self.model = model
        self.tools = tools
        self.verbose = verbose
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end
        self.on_iteration = on_iteration

        # Filter tools based on config
        self.available_tools = self._filter_tools()

        # Bind tools to model
        self.model_with_tools = self.model.bind_tools(self.available_tools)

        # Create tool map for execution
        self.tool_map = {tool.name: tool for tool in self.available_tools}

        # Create agent prompt
        self.prompt = self._create_prompt()

    def _filter_tools(self) -> List[BaseTool]:
        """Filter tools based on agent configuration."""
        if "*" in self.config.tools:
            return self.tools

        # Filter by name
        return [tool for tool in self.tools if tool.name in self.config.tools]

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
        Execute a task using the agent with tool calling support.

        Args:
            task: Task description
            chat_history: Optional chat history

        Returns:
            Dictionary with 'output', 'messages', and tool execution details
        """
        # Initialize messages
        messages = [SystemMessage(content=self.config.system_prompt)]

        if chat_history:
            messages.extend(chat_history)

        messages.append(HumanMessage(content=task))

        # Execution loop
        iteration = 0
        tool_calls_history = []

        while iteration < self.config.max_iterations:
            iteration += 1

            if self.verbose:
                print(f"\n=== Iteration {iteration} ===")

            # Call model with tools
            response = self.model_with_tools.invoke(messages)
            messages.append(response)

            # Check if there are tool calls
            if not response.tool_calls:
                # No more tool calls, return final response
                return {
                    "output": response.content,
                    "messages": messages,
                    "tool_calls": tool_calls_history,
                    "iterations": iteration,
                }

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call.get("id", "")

                if self.verbose:
                    print(f"\nTool Call: {tool_name}")
                    print(f"Arguments: {tool_args}")

                # Callback: tool start (only call if it's synchronous)
                if self.on_tool_start:
                    import inspect
                    if not inspect.iscoroutinefunction(self.on_tool_start):
                        self.on_tool_start(tool_name, tool_args)

                # Execute tool
                if tool_name in self.tool_map:
                    try:
                        tool = self.tool_map[tool_name]
                        result = tool.invoke(tool_args)

                        if self.verbose:
                            print(f"Result: {result[:200]}..." if len(str(result)) > 200 else f"Result: {result}")

                        # Callback: tool end (only call if it's synchronous)
                        if self.on_tool_end:
                            import inspect
                            if not inspect.iscoroutinefunction(self.on_tool_end):
                                self.on_tool_end(tool_name, tool_args, result)

                        # Add tool result to messages
                        tool_message = ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        messages.append(tool_message)

                        # Track tool call
                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "result": result,
                        })

                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        if self.verbose:
                            print(f"Error: {error_msg}")

                        # Add error message
                        tool_message = ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        messages.append(tool_message)

                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "error": str(e),
                        })
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    if self.verbose:
                        print(f"Error: {error_msg}")

                    tool_message = ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                    messages.append(tool_message)

        # Max iterations reached
        return {
            "output": "Maximum iterations reached without completion",
            "messages": messages,
            "tool_calls": tool_calls_history,
            "iterations": iteration,
        }

    async def arun(
        self, task: str, chat_history: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a task asynchronously with tool calling support.

        Args:
            task: Task description
            chat_history: Optional chat history

        Returns:
            Dictionary with 'output', 'messages', and tool execution details
        """
        # Initialize messages
        messages = [SystemMessage(content=self.config.system_prompt)]

        if chat_history:
            messages.extend(chat_history)

        messages.append(HumanMessage(content=task))

        # Execution loop
        iteration = 0
        tool_calls_history = []

        while iteration < self.config.max_iterations:
            iteration += 1

            if self.verbose:
                print(f"\n=== Iteration {iteration} ===")

            # Callback: iteration start
            if self.on_iteration:
                import inspect
                if inspect.iscoroutinefunction(self.on_iteration):
                    await self.on_iteration(iteration)
                else:
                    self.on_iteration(iteration)

            # Call model with tools
            response = await self.model_with_tools.ainvoke(messages)
            messages.append(response)

            # Check if there are tool calls
            if not response.tool_calls:
                # No more tool calls, return final response
                return {
                    "output": response.content,
                    "messages": messages,
                    "tool_calls": tool_calls_history,
                    "iterations": iteration,
                }

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call.get("id", "")

                if self.verbose:
                    print(f"\nTool Call: {tool_name}")
                    print(f"Arguments: {tool_args}")

                # Callback: tool start
                if self.on_tool_start:
                    import inspect
                    if inspect.iscoroutinefunction(self.on_tool_start):
                        await self.on_tool_start(tool_name, tool_args)
                    else:
                        self.on_tool_start(tool_name, tool_args)

                # Execute tool (async if available, otherwise sync)
                if tool_name in self.tool_map:
                    try:
                        tool = self.tool_map[tool_name]

                        # Try async invoke first
                        if hasattr(tool, "ainvoke"):
                            result = await tool.ainvoke(tool_args)
                        else:
                            result = tool.invoke(tool_args)

                        if self.verbose:
                            print(f"Result: {result[:200]}..." if len(str(result)) > 200 else f"Result: {result}")

                        # Callback: tool end
                        if self.on_tool_end:
                            import inspect
                            if inspect.iscoroutinefunction(self.on_tool_end):
                                await self.on_tool_end(tool_name, tool_args, result)
                            else:
                                self.on_tool_end(tool_name, tool_args, result)

                        # Add tool result to messages
                        tool_message = ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        messages.append(tool_message)

                        # Track tool call
                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "result": str(result)[:500],  # Truncate for history
                        })

                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        if self.verbose:
                            print(f"Error: {error_msg}")

                        # Add error message
                        tool_message = ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        messages.append(tool_message)

                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "error": str(e),
                        })
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    if self.verbose:
                        print(f"Error: {error_msg}")

                    tool_message = ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                    messages.append(tool_message)

        # Max iterations reached
        return {
            "output": "Maximum iterations reached without completion",
            "messages": messages,
            "tool_calls": tool_calls_history,
            "iterations": iteration,
        }

    async def arun_streaming(
        self, task: str, chat_history: Optional[List[Any]] = None
    ):
        """
        Execute a task asynchronously with streaming support.

        Yields chunks of the response as they arrive from the model.

        Args:
            task: Task description
            chat_history: Optional chat history

        Yields:
            Dict with 'type', 'content', and optional 'metadata'
        """
        from typing import AsyncGenerator

        # Initialize messages
        messages = [SystemMessage(content=self.config.system_prompt)]

        if chat_history:
            messages.extend(chat_history)

        messages.append(HumanMessage(content=task))

        # Execution loop
        iteration = 0
        tool_calls_history = []

        while iteration < self.config.max_iterations:
            iteration += 1

            if self.verbose:
                print(f"\n=== Iteration {iteration} ===")

            # Callback: iteration start
            if self.on_iteration:
                import inspect
                if inspect.iscoroutinefunction(self.on_iteration):
                    await self.on_iteration(iteration)
                else:
                    self.on_iteration(iteration)

            # Call model with streaming
            full_response_content = ""
            tool_calls = []

            async for chunk in self.model_with_tools.astream(messages):
                # Check if chunk has content
                if hasattr(chunk, 'content') and chunk.content:
                    full_response_content += chunk.content
                    # Yield content chunk immediately
                    yield {
                        "type": "chunk",
                        "content": chunk.content,
                        "metadata": {"iteration": iteration}
                    }

                # Collect tool calls from chunk
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)

            # Create response message
            from langchain_core.messages import AIMessage
            response = AIMessage(content=full_response_content, tool_calls=tool_calls)
            messages.append(response)

            # Check if there are tool calls
            if not response.tool_calls:
                # No more tool calls, return final response
                yield {
                    "type": "complete",
                    "content": full_response_content,
                    "metadata": {
                        "messages": messages,
                        "tool_calls": tool_calls_history,
                        "iterations": iteration,
                    }
                }
                return

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call.get("id", "")

                if self.verbose:
                    print(f"\nTool Call: {tool_name}")
                    print(f"Arguments: {tool_args}")

                # Callback: tool start
                if self.on_tool_start:
                    import inspect
                    if inspect.iscoroutinefunction(self.on_tool_start):
                        await self.on_tool_start(tool_name, tool_args)
                    else:
                        self.on_tool_start(tool_name, tool_args)

                # Execute tool (async if available, otherwise sync)
                if tool_name in self.tool_map:
                    try:
                        tool = self.tool_map[tool_name]

                        # Try async invoke first
                        if hasattr(tool, "ainvoke"):
                            result = await tool.ainvoke(tool_args)
                        else:
                            result = tool.invoke(tool_args)

                        if self.verbose:
                            print(f"Result: {result[:200]}..." if len(str(result)) > 200 else f"Result: {result}")

                        # Callback: tool end
                        if self.on_tool_end:
                            import inspect
                            if inspect.iscoroutinefunction(self.on_tool_end):
                                await self.on_tool_end(tool_name, tool_args, result)
                            else:
                                self.on_tool_end(tool_name, tool_args, result)

                        # Add tool result to messages
                        tool_message = ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        messages.append(tool_message)

                        # Track tool call
                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "result": str(result)[:500],  # Truncate for history
                        })

                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        if self.verbose:
                            print(f"Error: {error_msg}")

                        # Add error message
                        tool_message = ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                        messages.append(tool_message)

                        tool_calls_history.append({
                            "name": tool_name,
                            "args": tool_args,
                            "error": str(e),
                        })
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    if self.verbose:
                        print(f"Error: {error_msg}")

                    tool_message = ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                    messages.append(tool_message)

        # Max iterations reached
        yield {
            "type": "complete",
            "content": "Maximum iterations reached without completion",
            "metadata": {
                "messages": messages,
                "tool_calls": tool_calls_history,
                "iterations": iteration,
            }
        }
