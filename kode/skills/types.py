"""Skill 系统类型定义"""

from dataclasses import dataclass, field
from typing import Optional, List, Literal, Dict, Any


@dataclass
class SkillDefinition:
    """Skill 定义数据类"""

    # 核心属性
    skill_name: str           # 完整名称 "namespace:name"
    display_name: str         # 显示名称
    description: str          # 描述
    markdown_content: str     # Markdown 内容

    # 可选配置
    allowed_tools: Optional[List[str]] = None
    argument_hint: Optional[str] = None
    when_to_use: Optional[str] = None
    version: Optional[str] = None
    model: Optional[str] = None

    # 行为控制
    user_invocable: bool = True
    disable_model_invocation: bool = False

    # 来源信息
    source: Literal['user', 'project', 'plugin', 'builtin'] = 'user'
    base_dir: str = ''
    file_path: str = ''

    # 额外的 frontmatter 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'skill_name': self.skill_name,
            'display_name': self.display_name,
            'description': self.description,
            'allowed_tools': self.allowed_tools,
            'argument_hint': self.argument_hint,
            'when_to_use': self.when_to_use,
            'version': self.version,
            'model': self.model,
            'user_invocable': self.user_invocable,
            'disable_model_invocation': self.disable_model_invocation,
            'source': self.source,
            'base_dir': self.base_dir,
            'file_path': self.file_path,
        }


@dataclass
class SkillExecutionResult:
    """Skill 执行结果"""

    success: bool
    output: str = ''
    error: str = ''
    command_name: str = ''
    allowed_tools: Optional[List[str]] = None
    model: Optional[str] = None
    skill_name: str = ''

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'success': self.success,
            'output': self.output,
        }
        if self.error:
            result['error'] = self.error
        if self.command_name:
            result['command_name'] = self.command_name
        if self.allowed_tools:
            result['allowed_tools'] = self.allowed_tools
        if self.model:
            result['model'] = self.model
        if self.skill_name:
            result['skill_name'] = self.skill_name
        return result
