"""Permission management system for secure tool access."""

from enum import Enum
from typing import Any, Dict, Optional


class PermissionLevel(str, Enum):
    """Permission levels for tool access."""

    ALWAYS_ALLOW = "always_allow"
    ASK_EACH_TIME = "ask_each_time"
    DENY = "deny"


class Permission:
    """Represents a permission for a specific tool or action."""

    def __init__(
        self,
        tool_name: str,
        level: PermissionLevel = PermissionLevel.ASK_EACH_TIME,
        params: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize permission.

        Args:
            tool_name: Name of the tool
            level: Permission level
            params: Optional parameters for the permission
        """
        self.tool_name = tool_name
        self.level = level
        self.params = params or {}


class PermissionManager:
    """
    Manages tool permissions and user approvals.

    Equivalent to TypeScript's permission system in src/permissions.ts
    """

    def __init__(self) -> None:
        """Initialize permission manager."""
        self._permissions: Dict[str, Permission] = {}
        self._session_approvals: Dict[str, bool] = {}

    def set_permission(self, tool_name: str, level: PermissionLevel) -> None:
        """
        Set permission level for a tool.

        Args:
            tool_name: Name of the tool
            level: Permission level to set
        """
        self._permissions[tool_name] = Permission(tool_name, level)

    def get_permission(self, tool_name: str) -> PermissionLevel:
        """
        Get permission level for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Permission level
        """
        if tool_name in self._permissions:
            return self._permissions[tool_name].level
        return PermissionLevel.ASK_EACH_TIME

    def request_permission(
        self, tool_name: str, action: str, details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Request permission to use a tool.

        Args:
            tool_name: Name of the tool
            action: Description of the action
            details: Additional details about the action

        Returns:
            True if permission granted, False otherwise
        """
        permission_level = self.get_permission(tool_name)

        if permission_level == PermissionLevel.ALWAYS_ALLOW:
            return True

        if permission_level == PermissionLevel.DENY:
            return False

        # ASK_EACH_TIME - check session cache first
        cache_key = f"{tool_name}:{action}"
        if cache_key in self._session_approvals:
            return self._session_approvals[cache_key]

        # In a real implementation, this would prompt the user
        # For now, we'll default to allowing
        # This should be replaced with actual user interaction
        approved = self._prompt_user(tool_name, action, details)
        self._session_approvals[cache_key] = approved
        return approved

    def _prompt_user(
        self, tool_name: str, action: str, details: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Prompt user for permission (placeholder).

        In actual implementation, this would show a prompt to the user.

        Args:
            tool_name: Name of the tool
            action: Description of the action
            details: Additional details

        Returns:
            True if approved
        """
        # TODO: Implement actual user prompting via CLI
        # This is a placeholder that always approves
        return True

    def clear_session_approvals(self) -> None:
        """Clear all session-specific approvals."""
        self._session_approvals.clear()

    def is_tool_allowed(self, tool_name: str, agent_tools: Optional[list[str]] = None) -> bool:
        """
        Check if a tool is allowed for an agent.

        Args:
            tool_name: Name of the tool
            agent_tools: List of tools allowed for the agent, or None for all

        Returns:
            True if tool is allowed
        """
        # If agent has no tool restrictions, allow all
        if agent_tools is None or "*" in agent_tools:
            return True

        # Check if tool is in agent's allowed list
        return tool_name in agent_tools