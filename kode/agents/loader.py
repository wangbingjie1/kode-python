"""Dynamic agent configuration loading with 5-tier priority system."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from .base import AgentConfig


class AgentLoader:
    """
    Load agent configurations from markdown files.

    Equivalent to TypeScript's agentLoader in src/utils/agentLoader.ts

    5-tier priority system:
    1. Built-in (code-embedded)
    2. ~/.claude/agents/ (Claude Code user directory compatibility)
    3. ~/.kode/agents/ (Kode user)
    4. ./.claude/agents/ (Claude Code project directory compatibility)
    5. ./.kode/agents/ (Kode project)
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize agent loader.

        Args:
            project_root: Project root directory (default: current working directory)
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._agent_cache: Dict[str, AgentConfig] = {}
        self._builtin_agents: Dict[str, AgentConfig] = {}

        # Register built-in agents
        self._register_builtin_agents()

    def _register_builtin_agents(self) -> None:
        """Register built-in agent configurations."""
        # General purpose agent
        general_agent = AgentConfig(
            name="general-purpose",
            description="General-purpose agent for researching complex questions and multi-step tasks",
            system_prompt="""You are a helpful AI assistant that can use tools to accomplish tasks.
You have access to various tools for reading files, executing commands, and searching code.
Break down complex tasks into smaller steps and use the appropriate tools for each step.
Always explain your reasoning and provide clear, actionable results.""",
            tools=["*"],  # All tools
        )
        self._builtin_agents["general-purpose"] = general_agent

        # Explore agent
        explore_agent = AgentConfig(
            name="explore",
            description="Fast agent specialized for exploring codebases",
            system_prompt="""You are a specialized codebase exploration agent.
Your goal is to quickly find files, search code, and answer questions about the codebase structure.
Use Glob for finding files by patterns, Grep for searching code content, and FileRead for examining files.
Be thorough but efficient - prioritize the most relevant information.""",
            tools=["FileRead", "Glob", "Grep", "Bash"],
        )
        self._builtin_agents["explore"] = explore_agent

    def get_agent_directories(self) -> List[Path]:
        """
        Get all agent directories in priority order.

        Returns:
            List of paths to check for agent files
        """
        home = Path.home()
        directories = [
            # 2. Claude Code user directory (compatibility)
            home / ".claude" / "agents",
            # 3. Kode user directory
            home / ".kode" / "agents",
            # 4. Claude Code project directory (compatibility)
            self.project_root / ".claude" / "agents",
            # 5. Kode project directory
            self.project_root / ".kode" / "agents",
        ]

        # Return only existing directories
        return [d for d in directories if d.exists() and d.is_dir()]

    @lru_cache(maxsize=128)
    def load_agent(self, name: str) -> Optional[AgentConfig]:
        """
        Load agent configuration by name.

        Searches in priority order:
        1. Built-in agents
        2-5. File-based agents from directories

        Args:
            name: Agent name

        Returns:
            AgentConfig if found, None otherwise
        """
        # Check cache first
        if name in self._agent_cache:
            return self._agent_cache[name]

        # 1. Check built-in agents
        if name in self._builtin_agents:
            return self._builtin_agents[name]

        # 2-5. Check directories
        for directory in self.get_agent_directories():
            agent_file = directory / f"{name}.md"
            if agent_file.exists():
                try:
                    config = self._load_agent_file(agent_file)
                    self._agent_cache[name] = config
                    return config
                except Exception as e:
                    print(f"Warning: Failed to load agent {name} from {agent_file}: {e}")
                    continue

        return None

    def _load_agent_file(self, path: Path) -> AgentConfig:
        """
        Load agent configuration from markdown file.

        Args:
            path: Path to agent markdown file

        Returns:
            AgentConfig instance

        Raises:
            ValueError: If file format is invalid
        """
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return AgentConfig.from_markdown(content)

    def list_agents(self) -> List[str]:
        """
        List all available agent names.

        Returns:
            List of agent names from all sources
        """
        agents = set(self._builtin_agents.keys())

        # Scan all directories
        for directory in self.get_agent_directories():
            for agent_file in directory.glob("*.md"):
                agents.add(agent_file.stem)

        return sorted(list(agents))

    def get_agent_info(self, name: str) -> Optional[Dict[str, str]]:
        """
        Get information about an agent.

        Args:
            name: Agent name

        Returns:
            Dictionary with agent info (name, description, source)
        """
        config = self.load_agent(name)
        if not config:
            return None

        # Determine source
        if name in self._builtin_agents:
            source = "built-in"
        else:
            for directory in self.get_agent_directories():
                agent_file = directory / f"{name}.md"
                if agent_file.exists():
                    source = str(directory)
                    break
            else:
                source = "unknown"

        return {
            "name": config.name,
            "description": config.description,
            "source": source,
            "tools": ", ".join(config.tools),
            "model": config.model or "default",
        }

    def clear_cache(self) -> None:
        """Clear the agent cache."""
        self._agent_cache.clear()
        self.load_agent.cache_clear()