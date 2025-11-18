"""清理 ontology_tools.py 中废弃的同步和旧版异步函数"""
import re

file_path = r"e:\AI\AI ERP\kode-python\kode\tools\ontology_tools.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 要删除的函数列表（包括函数定义到下一个函数定义之前的所有内容）
functions_to_remove = [
    "_build_ontology_with_ai_sync",
    "_build_ontology_with_ai_async",
    "_extract_schema_skeleton",
    "_ai_analyze_global_architecture",
    "_build_domains_parallel",
    "_ai_refine_cross_domain_relationships",
]

# 读取所有行
lines = content.split("\n")
output_lines = []
skip_until_next_def = False
current_indent = None

i = 0
while i < len(lines):
    line = lines[i]

    # 检查是否是要删除的函数定义
    is_target_func = False
    for func_name in functions_to_remove:
        if f"def {func_name}(" in line or f"async def {func_name}(" in line:
            is_target_func = True
            # 记录当前缩进级别
            current_indent = len(line) - len(line.lstrip())
            skip_until_next_def = True
            print(f"Removing function: {func_name} (line {i+1})")
            break

    if skip_until_next_def:
        # 检查是否遇到同级或更外层的 def/class/async def
        if line.strip() and not line.strip().startswith("#") and not line.strip().startswith('"""'):
            line_indent = len(line) - len(line.lstrip())
            if ("def " in line or "class " in line or "async def " in line) and line_indent <= current_indent:
                # 遇到下一个同级函数，停止跳过
                skip_until_next_def = False
                current_indent = None
                # 保留这一行（下一个函数的开始）
                if not is_target_func:
                    output_lines.append(line)
            # else: 继续跳过
        # else: 空行或注释，继续跳过
    else:
        # 正常保留
        output_lines.append(line)

    i += 1

# 写回文件
with open(file_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"\nCleanup complete! Removed {len(functions_to_remove)} deprecated functions")
