"""Main CLI entry point using Typer."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from kode.agents import AgentLoader
from kode.utils import ConfigManager

from .repl import REPL

app = typer.Typer(
    name="kode",
    help="AI-native coding assistant powered by LangChain",
    add_completion=False,
    invoke_without_command=True,  # Allow calling without a command
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project root directory"
    ),
) -> None:
    """Start Kode interactive session (default command)."""
    # If a subcommand was invoked, don't run the interactive session
    if ctx.invoked_subcommand is not None:
        return

    # Load configuration
    cli_params = {}
    if model:
        cli_params["models"] = {"main": model}
    if verbose:
        cli_params["verbose"] = verbose

    project_root = project or str(Path.cwd())
    config_manager = ConfigManager(project_root=project_root, cli_params=cli_params)

    # Start REPL
    repl = REPL(config_manager=config_manager)
    repl.run()


@app.command()
def run(
    task: str = typer.Argument(..., help="Task to execute"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project root directory"
    ),
) -> None:
    """Execute a single task and exit."""
    # Load configuration
    cli_params = {}
    if model:
        cli_params["models"] = {"main": model}
    if verbose:
        cli_params["verbose"] = verbose

    project_root = project or str(Path.cwd())
    config_manager = ConfigManager(project_root=project_root, cli_params=cli_params)

    # Execute task
    repl = REPL(config_manager=config_manager)
    repl.execute_single_task(task)


@app.command()
def agents(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all available agents"),
    info: Optional[str] = typer.Option(None, "--info", "-i", help="Show agent information"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project root directory"
    ),
) -> None:
    """Manage agents."""
    project_root = project or str(Path.cwd())
    loader = AgentLoader(project_root=project_root)

    if list_all:
        agent_list = loader.list_agents()
        console.print("\n[bold]Available Agents:[/bold]\n")
        for agent_name in agent_list:
            agent_info = loader.get_agent_info(agent_name)
            if agent_info:
                console.print(f"  [cyan]{agent_name}[/cyan] - {agent_info['description']}")
        console.print()

    elif info:
        agent_info = loader.get_agent_info(info)
        if agent_info:
            console.print(f"\n[bold]Agent: {agent_info['name']}[/bold]")
            console.print(f"Description: {agent_info['description']}")
            console.print(f"Source: {agent_info['source']}")
            console.print(f"Tools: {agent_info['tools']}")
            console.print(f"Model: {agent_info['model']}\n")
        else:
            console.print(f"[red]Agent '{info}' not found[/red]")

    else:
        console.print("[yellow]Use --list to see all agents or --info <name> for details[/yellow]")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    init: bool = typer.Option(
        False, "--init", "-i", help="Create example configuration file"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project root directory"
    ),
) -> None:
    """Manage configuration."""
    project_root = project or str(Path.cwd())
    config_manager = ConfigManager(project_root=project_root)

    if show:
        import json

        config_data = config_manager.get_all()
        # Mask API keys
        if "apiKeys" in config_data:
            for key in config_data["apiKeys"]:
                if config_data["apiKeys"][key]:
                    config_data["apiKeys"][key] = "***masked***"

        console.print("\n[bold]Current Configuration:[/bold]\n")
        console.print(json.dumps(config_data, indent=2))
        console.print()

    elif init:
        config_manager.create_example_config()

    else:
        console.print("[yellow]Use --show to see config or --init to create example[/yellow]")


@app.command()
def version() -> None:
    """Show version information."""
    from kode import __version__

    console.print(f"Kode version {__version__}")


if __name__ == "__main__":
    app()