"""Advanced tools for complex operations."""

import json
from pathlib import Path
from typing import List, Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class EditItem(BaseModel):
    """A single edit operation."""
    file_path: str = Field(description="Path to the file to edit")
    old_string: str = Field(description="String to find and replace")
    new_string: str = Field(description="Replacement string")


class MultiEditInput(BaseModel):
    """Input for MultiEditTool."""

    edits: List[EditItem] = Field(
        description="List of edit operations, each with file_path, old_string, and new_string"
    )


class MultiEditTool(KodeTool):
    """
    Edit multiple files at once.

    Equivalent to TypeScript's MultiEditTool
    """

    name: str = "MultiEdit"
    description: str = """Edit multiple files in a single operation.
- Performs exact string replacements across multiple files
- Input is JSON array: [{"file_path": "path", "old_string": "old", "new_string": "new"}]
- All edits are atomic - if one fails, all fail
- Useful for renaming across multiple files"""
    args_schema: Type[BaseModel] = MultiEditInput
    requires_permission: bool = True

    def _run(self, edits: List[EditItem]) -> str:
        """Perform multiple edits."""
        try:
            results = []
            failed = []

            for i, edit in enumerate(edits):
                # Convert EditItem to dict if needed
                if hasattr(edit, 'model_dump'):
                    edit_dict = edit.model_dump()
                else:
                    edit_dict = edit

                file_path = edit_dict.get("file_path")
                old_string = edit_dict.get("old_string")
                new_string = edit_dict.get("new_string")

                try:
                    path = Path(file_path)
                    if not path.exists():
                        failed.append(f"Edit {i}: File not found: {file_path}")
                        continue

                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if old_string not in content:
                        failed.append(f"Edit {i}: String not found in {file_path}")
                        continue

                    new_content = content.replace(old_string, new_string)

                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    results.append(f"Edit {i}: Updated {file_path}")

                except Exception as e:
                    failed.append(f"Edit {i}: {str(e)}")

            summary = f"Completed {len(results)}/{len(edits)} edits"
            if failed:
                summary += f"\nFailed:\n" + "\n".join(failed)
            if results:
                summary += f"\nSuccess:\n" + "\n".join(results)

            return summary

        except Exception as e:
            return f"Error: {str(e)}"


class ThinkInput(BaseModel):
    """Input for ThinkTool."""

    thought: str = Field(description="Your reasoning or thought process")


class ThinkTool(KodeTool):
    """
    Record reasoning and thought process.

    Equivalent to TypeScript's ThinkTool
    """

    name: str = "Think"
    description: str = """Record your reasoning and thought process.
- Use this to show your thinking before taking action
- Helps explain complex decisions
- Makes your reasoning transparent
- Not executed, just recorded for context"""
    args_schema: Type[BaseModel] = ThinkInput
    requires_permission: bool = False

    def _run(self, thought: str) -> str:
        """Record thought."""
        return f"💭 Thinking: {thought}"


class TodoItem(BaseModel):
    """A single todo item."""
    content: str = Field(description="Task description (imperative form)")
    status: str = Field(description="Task status: pending, in_progress, or completed")
    activeForm: str = Field(description="Present continuous form of the task")


class TodoWriteInput(BaseModel):
    """Input for TodoWriteTool."""

    todos: List[TodoItem] = Field(
        description="List of todo items, each with content, status, and activeForm"
    )


class TodoWriteTool(KodeTool):
    """
    Manage todo list for tracking tasks.

    Equivalent to TypeScript's TodoWriteTool
    """

    name: str = "TodoWrite"
    description: str = """Manage todo list for task tracking.
- Create and update todos
- Track task progress (pending, in_progress, completed)
- Each todo has: content (what to do), status, activeForm (present continuous)
- Useful for complex multi-step tasks
- Only one task should be in_progress at a time"""
    args_schema: Type[BaseModel] = TodoWriteInput
    requires_permission: bool = False

    def _get_todo_path(self) -> Path:
        """Get the todo file path."""
        return Path.cwd() / ".kode" / "todos.json"

    def _run(self, todos: List[TodoItem]) -> str:
        """Update todos."""
        try:
            todo_path = self._get_todo_path()

            # Convert TodoItem objects to dicts
            todo_list = [todo.model_dump() if hasattr(todo, 'model_dump') else todo for todo in todos]

            # Validate todos
            for todo in todo_list:
                if todo["status"] not in ["pending", "in_progress", "completed"]:
                    return f"Error: Invalid status: {todo['status']}"

            # Save todos
            todo_path.parent.mkdir(parents=True, exist_ok=True)
            with open(todo_path, "w", encoding="utf-8") as f:
                json.dump(todo_list, f, indent=2)

            # Generate summary
            pending = sum(1 for t in todo_list if t["status"] == "pending")
            in_progress = sum(1 for t in todo_list if t["status"] == "in_progress")
            completed = sum(1 for t in todo_list if t["status"] == "completed")

            summary = f"Todos updated: {len(todo_list)} total\n"
            summary += f"  Pending: {pending}\n"
            summary += f"  In Progress: {in_progress}\n"
            summary += f"  Completed: {completed}"

            return summary

        except Exception as e:
            return f"Error: {str(e)}"


class TaskInput(BaseModel):
    """Input for TaskTool."""

    description: str = Field(description="Short task description (3-5 words)")
    prompt: str = Field(description="Detailed task prompt for the sub-agent")
    subagent_type: str = Field(description="Type of agent to use (e.g., 'explore', 'general-purpose')")
    model: Optional[str] = Field(default=None, description="Optional model to use")


class TaskTool(KodeTool):
    """
    Delegate tasks to specialized sub-agents.

    Equivalent to TypeScript's TaskTool
    """

    name: str = "Task"
    description: str = """Delegate complex tasks to specialized sub-agents.
- Launch sub-agents for specific tasks
- Each agent has specialized capabilities
- Agents work autonomously and return results
- Use for: research, code search, complex analysis
- Available agents: explore, general-purpose, etc."""
    args_schema: Type[BaseModel] = TaskInput
    requires_permission: bool = False

    def _run(
        self,
        description: str,
        prompt: str,
        subagent_type: str,
        model: Optional[str] = None,
    ) -> str:
        """Delegate to sub-agent."""
        # This is a placeholder - actual implementation would create a sub-agent
        # and execute the task. For now, we return a message.
        return f"""Task delegated: {description}

Agent: {subagent_type}
Model: {model or 'default'}
Prompt: {prompt}

[Note: TaskTool requires full agent system integration]
[This is a placeholder response - actual sub-agent execution not yet implemented]"""
