"""Skill 加载器 - 从文件系统加载 skills"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from .types import SkillDefinition


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    解析 YAML frontmatter

    Args:
        content: 文件内容

    Returns:
        (frontmatter 字典, markdown 内容)
    """
    pattern = r'^---\s*\n([\s\S]*?)---\s*\n?'
    match = re.match(pattern, content)

    if not match:
        return {}, content

    frontmatter = {}
    yaml_content = match.group(1)

    for line in yaml_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()

            # 移除引号
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            frontmatter[key] = value

    markdown = content[match.end():]
    return frontmatter, markdown


def load_skill_from_file(
    file_path: Path,
    namespace: str,
    skill_name_override: Optional[str] = None
) -> Optional[SkillDefinition]:
    """
    从文件加载单个 skill

    Args:
        file_path: SKILL.md 文件路径
        namespace: 命名空间 (user/project/plugin/builtin)
        skill_name_override: 覆盖的 skill 名称

    Returns:
        SkillDefinition 或 None
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        frontmatter, markdown = parse_frontmatter(content)

        # 提取 skill 名称
        skill_dir = file_path.parent
        base_name = skill_name_override or skill_dir.name
        skill_name = f"{namespace}:{base_name}"

        # 解析 allowed-tools
        allowed_tools = None
        if 'allowed-tools' in frontmatter:
            allowed_tools = [t.strip() for t in frontmatter['allowed-tools'].split(',')]

        # 解析布尔值
        def parse_bool(value: str, default: bool = False) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1')
            return default

        return SkillDefinition(
            skill_name=skill_name,
            display_name=frontmatter.get('name', base_name),
            description=frontmatter.get('description', ''),
            markdown_content=markdown.strip(),
            allowed_tools=allowed_tools,
            argument_hint=frontmatter.get('argument-hint'),
            when_to_use=frontmatter.get('when-to-use') or frontmatter.get('when_to_use'),
            version=frontmatter.get('version'),
            model=frontmatter.get('model'),
            user_invocable=parse_bool(frontmatter.get('user-invocable', 'true'), True),
            disable_model_invocation=parse_bool(
                frontmatter.get('disable-model-invocation', 'false'), False
            ),
            source=namespace,
            base_dir=str(skill_dir),
            file_path=str(file_path),
            metadata=frontmatter,
        )
    except Exception as e:
        print(f"[SkillLoader] 加载 skill 失败: {file_path}, 错误: {e}")
        return None


def load_skills_from_directory(
    dir_path: Path,
    namespace: str
) -> List[SkillDefinition]:
    """
    扫描目录加载所有 skills

    目录结构支持：
    1. 单文件模式: dir_path/SKILL.md
    2. 多文件模式: dir_path/<skill_name>/SKILL.md

    Args:
        dir_path: 目录路径
        namespace: 命名空间

    Returns:
        SkillDefinition 列表
    """
    results = []

    if not dir_path.exists():
        return results

    # 检查根目录的 SKILL.md（单文件模式）
    root_skill = dir_path / 'SKILL.md'
    if root_skill.exists():
        skill = load_skill_from_file(root_skill, namespace)
        if skill:
            results.append(skill)
        return results

    # 遍历子目录（多文件模式）
    for entry in dir_path.iterdir():
        if entry.is_dir() or entry.is_symlink():
            # 检查 SKILL.md 或 skill.md
            skill_file = entry / 'SKILL.md'
            if not skill_file.exists():
                skill_file = entry / 'skill.md'

            if skill_file.exists():
                skill = load_skill_from_file(skill_file, namespace)
                if skill:
                    results.append(skill)

    return results


def get_user_skills_dir() -> Path:
    """获取用户级 skills 目录 (~/.kode/skills/)"""
    home = Path.home()
    return home / '.kode' / 'skills'


def get_project_skills_dir(project_root: Optional[Path] = None) -> Path:
    """获取项目级 skills 目录 (./.kode/skills/)"""
    if project_root is None:
        project_root = Path.cwd()
    return project_root / '.kode' / 'skills'


def get_builtin_skills_dir() -> Path:
    """获取内置 skills 目录"""
    # 内置 skills 放在 kode/skills/builtin/ 目录下
    return Path(__file__).parent / 'builtin'
