"""Skill 注册表 - 管理和查找 skills"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

from .types import SkillDefinition, SkillExecutionResult
from .loader import (
    load_skills_from_directory,
    get_user_skills_dir,
    get_project_skills_dir,
    get_builtin_skills_dir,
)


class SkillRegistry:
    """
    Skill 注册表

    管理所有加载的 skills，支持：
    - 用户级 skills (~/.kode/skills/)
    - 项目级 skills (./.kode/skills/)
    - 内置 skills (kode/skills/builtin/)

    优先级：项目级 > 用户级 > 内置
    """

    def __init__(self):
        self._registry: Dict[str, SkillDefinition] = {}
        self._loaded = False
        self._invoked_skills: Dict[str, Dict[str, Any]] = {}

    def initialize(self, project_root: Optional[Path] = None) -> None:
        """
        初始化 skills 系统

        Args:
            project_root: 项目根目录（可选）
        """
        self._registry.clear()
        self._invoked_skills.clear()

        # 1. 加载内置 skills (优先级最低)
        builtin_dir = get_builtin_skills_dir()
        for skill in load_skills_from_directory(builtin_dir, 'builtin'):
            self._registry[skill.skill_name] = skill

        # 2. 加载用户级 skills
        user_dir = get_user_skills_dir()
        for skill in load_skills_from_directory(user_dir, 'user'):
            self._registry[skill.skill_name] = skill

        # 3. 加载项目级 skills (优先级最高，会覆盖同名 skill)
        project_dir = get_project_skills_dir(project_root)
        for skill in load_skills_from_directory(project_dir, 'project'):
            self._registry[skill.skill_name] = skill

        self._loaded = True

    def register(self, skill: SkillDefinition) -> None:
        """
        手动注册一个 skill

        Args:
            skill: SkillDefinition 实例
        """
        self._registry[skill.skill_name] = skill

    def unregister(self, skill_name: str) -> bool:
        """
        注销一个 skill

        Args:
            skill_name: skill 名称

        Returns:
            是否成功注销
        """
        if skill_name in self._registry:
            del self._registry[skill_name]
            return True
        return False

    def get(self, skill_name: str) -> Optional[SkillDefinition]:
        """
        获取 skill（精确匹配）

        Args:
            skill_name: skill 名称（如 "user:my-skill" 或 "my-skill"）

        Returns:
            SkillDefinition 或 None
        """
        if not self._loaded:
            self.initialize()

        # 精确匹配
        if skill_name in self._registry:
            return self._registry[skill_name]

        # 模糊匹配（不含命名空间时）
        if ':' not in skill_name:
            for full_name, skill in self._registry.items():
                name = full_name.split(':')[-1]
                if name == skill_name:
                    return skill

        return None

    def find(self, skill_input: str) -> Optional[SkillDefinition]:
        """find 是 get 的别名"""
        return self.get(skill_input)

    def get_all(self) -> List[SkillDefinition]:
        """获取所有已注册的 skills"""
        if not self._loaded:
            self.initialize()
        return list(self._registry.values())

    def get_user_invocable(self) -> List[SkillDefinition]:
        """获取所有可用户调用的 skills"""
        return [s for s in self.get_all() if s.user_invocable]

    def execute(
        self,
        skill_input: str,
        args: Optional[str] = None
    ) -> SkillExecutionResult:
        """
        执行 skill

        Args:
            skill_input: skill 名称
            args: 可选参数

        Returns:
            SkillExecutionResult
        """
        if not self._loaded:
            self.initialize()

        skill = self.find(skill_input)
        if not skill:
            return SkillExecutionResult(
                success=False,
                error=f'Skill not found: {skill_input}'
            )

        if skill.disable_model_invocation:
            return SkillExecutionResult(
                success=False,
                error='Skill invocation disabled by configuration'
            )

        # 构建内容
        content = skill.markdown_content
        if args:
            content += f'\n\n**ARGUMENTS:** {args}'

        # 记录已调用的 skill
        self._record_invoked(skill, content)

        # 构建 skill 消息内容（对齐官网格式）
        skill_message = f'<command-message>The "{skill.display_name}" skill is loading</command-message>\n\n'
        skill_message += f'<skill name="{skill.skill_name}" location="{skill.source}"'

        if skill.version:
            skill_message += f' version="{skill.version}"'
        if skill.model:
            skill_message += f' model="{skill.model}"'
        if skill.allowed_tools:
            skill_message += f' allowed-tools="{",".join(skill.allowed_tools)}"'

        skill_message += f'>\n{content}\n</skill>'

        # 对齐官网实现：
        # - output（tool_result 内容）只是简短的 "Launching skill: xxx"
        # - skill 的完整内容通过 new_messages 作为独立的 user 消息传递
        return SkillExecutionResult(
            success=True,
            output=f'Launching skill: {skill.display_name}',  # 简短的 tool_result
            command_name=skill.display_name,
            allowed_tools=skill.allowed_tools,
            model=skill.model,
            skill_name=skill.skill_name,
            # skill 内容作为独立的 user 消息（对齐官网实现）
            new_messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': skill_message,
                        }
                    ],
                }
            ],
        )

    def _record_invoked(self, skill: SkillDefinition, content: str) -> None:
        """记录已调用的 skill"""
        self._invoked_skills[skill.skill_name] = {
            'skill_name': skill.skill_name,
            'skill_path': skill.file_path,
            'content': content,
            'invoked_at': datetime.now().isoformat(),
        }

    def get_invoked_skills(self) -> Dict[str, Dict[str, Any]]:
        """获取已调用的 skills 记录"""
        return self._invoked_skills.copy()

    def generate_tool_description(self) -> str:
        """
        生成 Skill 工具的描述（给 AI 看的）

        Returns:
            工具描述字符串
        """
        skills = self.get_user_invocable()

        if not skills:
            return "Execute a skill. No skills are currently available."

        skills_xml = '\n'.join([
            f'''<skill>
<name>{s.skill_name}</name>
<description>{s.description}</description>
<location>{s.source}</location>
</skill>'''
            for s in skills
        ])

        return f'''Execute a skill within the main conversation.

When users ask you to run a "slash command" like "/pdf" or "/docx", use this tool.

<available_skills>
{skills_xml}
</available_skills>
'''


# 全局单例
_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """获取全局 Skill 注册表单例"""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def initialize_skills(project_root: Optional[Path] = None) -> None:
    """初始化 skills 系统"""
    get_skill_registry().initialize(project_root)


def find_skill(skill_input: str) -> Optional[SkillDefinition]:
    """查找 skill"""
    return get_skill_registry().find(skill_input)


def execute_skill(skill_input: str, args: Optional[str] = None) -> SkillExecutionResult:
    """执行 skill"""
    return get_skill_registry().execute(skill_input, args)


def get_all_skills() -> List[SkillDefinition]:
    """获取所有 skills"""
    return get_skill_registry().get_all()
