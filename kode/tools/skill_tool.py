"""Skill 工具 - 执行 skills"""

from typing import Optional, Type

from pydantic import BaseModel, Field

from .base import KodeTool
from kode.skills import (
    get_skill_registry,
    initialize_skills,
    SkillExecutionResult,
)


class SkillInput(BaseModel):
    """Skill 工具输入参数"""

    skill: str = Field(
        ...,
        description="要调用的 skill 名称，例如 'pdf', 'docx', 'user:my-skill'"
    )
    args: Optional[str] = Field(
        None,
        description="可选的参数，传递给 skill"
    )


class SkillTool(KodeTool):
    """
    Skill 执行工具

    用于执行已注册的 skills，支持：
    - 用户级 skills (~/.kode/skills/)
    - 项目级 skills (./.kode/skills/)
    - 内置 skills (kode/skills/builtin/)

    用法示例：
    - /pdf - 调用 PDF 处理 skill
    - /docx - 调用 Word 文档处理 skill
    - /xlsx - 调用 Excel 处理 skill
    """

    name: str = "Skill"
    description: str = "Execute a skill. Use this tool to run document processing skills like /pdf, /docx, /xlsx, /pptx."
    args_schema: Type[BaseModel] = SkillInput
    requires_permission: bool = False

    _initialized: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_initialized()
        # 动态更新 description
        self.description = get_skill_registry().generate_tool_description()

    def _ensure_initialized(self) -> None:
        """确保 skills 系统已初始化"""
        if not self._initialized:
            initialize_skills()
            self._initialized = True

    def _run(self, skill: str, args: Optional[str] = None) -> str:
        """
        执行 skill

        Args:
            skill: skill 名称
            args: 可选参数

        Returns:
            执行结果
        """
        self._ensure_initialized()

        result: SkillExecutionResult = get_skill_registry().execute(skill, args)

        if not result.success:
            return f"Error: {result.error}"

        return result.output

    async def _arun(self, skill: str, args: Optional[str] = None) -> str:
        """异步执行 skill"""
        return self._run(skill, args)
