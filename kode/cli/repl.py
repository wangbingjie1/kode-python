"""Interactive REPL for Kode."""

from typing import Any, Dict, List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from kode.agents import AgentLoader, KodeAgent
from kode.core import ModelManager, PermissionManager
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
from kode.utils import ConfigManager, setup_logger


class REPL:
    """
    Interactive Read-Eval-Print Loop for Kode.

    Equivalent to TypeScript's REPL in src/screens/REPL.tsx
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize REPL.

        Args:
            config_manager: Configuration manager
        """
        self.config = config_manager
        self.console = Console()
        self.logger = setup_logger(verbose=config_manager.get("verbose", False))

        # Initialize components
        self.model_manager = ModelManager(config_manager.get_all())
        self.permission_manager = PermissionManager()
        self.agent_loader = AgentLoader(project_root=str(config_manager.project_root))

        # Setup tools (all 17 tools)
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

        # Chat history
        self.chat_history: List[Any] = []

        # Prompt session
        self.session = PromptSession(history=InMemoryHistory())

    def run(self) -> None:
        """Run the interactive REPL."""
        self._show_welcome()

        while True:
            try:
                # Get user input
                user_input = self.session.prompt("\n> ")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Execute task
                self._execute_task(user_input)

            except KeyboardInterrupt:
                continue
            except EOFError:
                self._show_goodbye()
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                if self.config.get("verbose"):
                    import traceback

                    self.console.print(traceback.format_exc())

    def execute_single_task(self, task: str) -> None:
        """
        Execute a single task and exit.

        Args:
            task: Task to execute
        """
        try:
            self._execute_task(task)
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            if self.config.get("verbose"):
                import traceback

                self.console.print(traceback.format_exc())

    def _execute_task(self, task: str) -> None:
        """Execute a task using the agent."""
        self.console.print("\n[dim]Thinking...[/dim]")

        # Get current model
        model = self.model_manager.get_model()

        # Create agent
        agent_config = self.agent_loader.load_agent("general-purpose")
        if not agent_config:
            self.console.print("[red]Error: Failed to load agent[/red]")
            return

        agent = KodeAgent(
            config=agent_config,
            model=model,
            tools=self.tools,
            verbose=self.config.get("verbose", False),
        )

        # Run agent
        try:
            result = agent.run(task, chat_history=self.chat_history)

            # Display result
            self._display_result(result)

            # Update chat history
            # This is simplified - in a real implementation, you'd track the full conversation
            self.chat_history.append({"role": "user", "content": task})
            self.chat_history.append({"role": "assistant", "content": result.get("output", "")})

        except Exception as e:
            self.console.print(f"[red]Error executing task: {e}[/red]")
            if self.config.get("verbose"):
                import traceback

                self.console.print(traceback.format_exc())

    def _display_result(self, result: Dict[str, Any]) -> None:
        """Display agent result."""
        output = result.get("output", "")
        if output:
            self.console.print()
            self.console.print(Panel(Markdown(output), title="Result", border_style="green"))

    def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0][1:]  # Remove leading /
        args = parts[1:]

        if cmd == "help":
            self._show_help()
        elif cmd == "exit" or cmd == "quit":
            self._show_goodbye()
            exit(0)
        elif cmd == "clear":
            self.console.clear()
            self.chat_history.clear()
            self.console.print("[dim]History cleared[/dim]")
        elif cmd == "model":
            self._handle_model_command(args)
        elif cmd == "agents":
            self._handle_agents_command(args)
        elif cmd == "config":
            self._show_config()
        else:
            self.console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
            self.console.print("[dim]Type /help for available commands[/dim]")

    def _handle_model_command(self, args: List[str]) -> None:
        """Handle model command."""
        if not args:
            current = self.model_manager.get_current_model_name()
            self.console.print(f"\n[bold]Current model:[/bold] {current}")
            self.console.print("\n[bold]Available models:[/bold]")
            for model_name in self.model_manager.list_models():
                self.console.print(f"  - {model_name}")
            self.console.print()
        else:
            model_name = args[0]
            try:
                self.model_manager.switch_model(model_name)
                self.console.print(f"[green]Switched to model: {model_name}[/green]")
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")

    def _handle_agents_command(self, args: List[str]) -> None:
        """Handle agents command."""
        agent_list = self.agent_loader.list_agents()
        self.console.print("\n[bold]Available Agents:[/bold]\n")
        for agent_name in agent_list:
            agent_info = self.agent_loader.get_agent_info(agent_name)
            if agent_info:
                self.console.print(f"  [cyan]{agent_name}[/cyan] - {agent_info['description']}")
        self.console.print()

    def _show_config(self) -> None:
        """Show current configuration."""
        import json

        config_data = self.config.get_all()
        # Mask API keys
        if "apiKeys" in config_data:
            for key in config_data["apiKeys"]:
                if config_data["apiKeys"][key]:
                    config_data["apiKeys"][key] = "***masked***"

        self.console.print("\n[bold]Current Configuration:[/bold]\n")
        self.console.print(json.dumps(config_data, indent=2))
        self.console.print()

    def _show_welcome(self) -> None:
        """Show welcome message."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]Kode[/bold cyan] - AI-native coding assistant\n"
                "[dim]Powered by LangChain[/dim]\n\n"
                "Type [bold]/help[/bold] for available commands",
                border_style="cyan",
            )
        )

    def _show_goodbye(self) -> None:
        """Show goodbye message."""
        self.console.print("\n[cyan]Goodbye![/cyan]\n")

    def _show_help(self) -> None:
        """Show help message."""
        help_text = """
[bold]Available Commands:[/bold]

  [cyan]/help[/cyan]           - Show this help message
  [cyan]/exit[/cyan] or [cyan]/quit[/cyan] - Exit Kode
  [cyan]/clear[/cyan]          - Clear chat history
  [cyan]/model[/cyan] [name]   - Switch model or list available models
  [cyan]/agents[/cyan]         - List available agents
  [cyan]/config[/cyan]         - Show current configuration

[bold]Usage:[/bold]

  Simply type your task or question and press Enter.
  Kode will use AI to understand and execute your request.

[bold]Examples:[/bold]

  > Analyze the structure of this codebase
  > Find all Python files in the src directory
  > Read the README.md file
  > Create a new feature for user authentication
        """
        self.console.print(Panel(help_text.strip(), title="Help", border_style="cyan"))