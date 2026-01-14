"""
Custom exceptions for Kode.
"""

from typing import Optional, List, Any


class KodeException(Exception):
    """Base exception for Kode."""
    pass


class UserInputRequired(KodeException):
    """
    Exception raised when agent needs user input.

    This is a special control-flow exception used to pause agent execution
    and request user interaction via the frontend.
    """

    def __init__(
        self,
        question: str,
        question_type: str = "text",
        options: Optional[List[str]] = None,
        default_value: Optional[str] = None,
        required: bool = True,
        context: Optional[str] = None,
        tool_instance: Optional[Any] = None,
        allow_defer: bool = False,
    ):
        """
        Initialize UserInputRequired exception.

        Args:
            question: Question text to display to user
            question_type: Type of question (text, select, multiselect, confirm)
            options: List of options for select/multiselect
            default_value: Default value
            required: Whether answer is required
            context: Additional context to help user understand
            tool_instance: Reference to the AskUserTool instance
            allow_defer: Whether user can choose to answer later (稍后回答)
        """
        self.question = question
        self.question_type = question_type
        self.options = options
        self.default_value = default_value
        self.required = required
        self.context = context
        self.tool_instance = tool_instance
        self.allow_defer = allow_defer
        super().__init__(f"User input required: {question}")

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "question": self.question,
            "question_type": self.question_type,
            "options": self.options,
            "default_value": self.default_value,
            "required": self.required,
            "context": self.context,
            "allow_defer": self.allow_defer,
        }
