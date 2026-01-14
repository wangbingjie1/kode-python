"""Kode Skills 系统

Skills 是可扩展的提示词模板系统，支持用户自定义命令。

目录结构：
- ~/.kode/skills/           # 用户级 (namespace: user)
- ./.kode/skills/           # 项目级 (namespace: project)
- kode/skills/builtin/      # 内置 skills (namespace: builtin)

每个 skill 是一个目录，包含 SKILL.md 文件：
    my-skill/
    └── SKILL.md

SKILL.md 格式：
    ---
    name: "Skill 显示名称"
    description: "Skill 描述"
    allowed-tools: "bash,read,write"
    argument-hint: "[--flag] <file>"
    when-to-use: "当用户需要..."
    version: "1.0"
    model: "opus"
    user-invocable: true
    ---

    # Skill 内容

    这里是实际的提示词内容。
"""

from .types import SkillDefinition, SkillExecutionResult
from .loader import (
    parse_frontmatter,
    load_skill_from_file,
    load_skills_from_directory,
    get_user_skills_dir,
    get_project_skills_dir,
    get_builtin_skills_dir,
)
from .registry import (
    SkillRegistry,
    get_skill_registry,
    initialize_skills,
    find_skill,
    execute_skill,
    get_all_skills,
)

__all__ = [
    # Types
    'SkillDefinition',
    'SkillExecutionResult',
    # Loader
    'parse_frontmatter',
    'load_skill_from_file',
    'load_skills_from_directory',
    'get_user_skills_dir',
    'get_project_skills_dir',
    'get_builtin_skills_dir',
    # Registry
    'SkillRegistry',
    'get_skill_registry',
    'initialize_skills',
    'find_skill',
    'execute_skill',
    'get_all_skills',
]
