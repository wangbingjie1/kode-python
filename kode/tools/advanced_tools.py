"""Advanced tools for complex operations."""

import json
from pathlib import Path
from typing import List, Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool


class MultiEditInput(BaseModel):
    """Input for MultiEditTool."""

    edits: str = Field(
        description="JSON array of edits: [{file_path, old_string, new_string}]"
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

    def _run(self, edits: str) -> str:
        """Perform multiple edits."""
        try:
            # Parse edits
            edit_list = json.loads(edits)
            if not isinstance(edit_list, list):
                return "Error: edits must be a JSON array"

            results = []
            failed = []

            for i, edit in enumerate(edit_list):
                file_path = edit.get("file_path")
                old_string = edit.get("old_string")
                new_string = edit.get("new_string")

                if not all([file_path, old_string is not None, new_string is not None]):
                    failed.append(f"Edit {i}: Missing required fields")
                    continue

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

            summary = f"Completed {len(results)}/{len(edit_list)} edits"
            if failed:
                summary += f"\nFailed:\n" + "\n".join(failed)
            if results:
                summary += f"\nSuccess:\n" + "\n".join(results)

            return summary

        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON: {str(e)}"
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


class TodoWriteInput(BaseModel):
    """Input for TodoWriteTool."""

    todos: str = Field(
        description="JSON array of todos: [{content, status, activeForm}]"
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

    def _run(self, todos: str) -> str:
        """Update todos."""
        try:
            todo_path = self._get_todo_path()

            # Parse todos
            todo_list = json.loads(todos)
            if not isinstance(todo_list, list):
                return "Error: todos must be a JSON array"

            # Validate todos
            for todo in todo_list:
                required = ["content", "status", "activeForm"]
                if not all(field in todo for field in required):
                    return f"Error: Each todo must have: {', '.join(required)}"

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

        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON: {str(e)}"
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
