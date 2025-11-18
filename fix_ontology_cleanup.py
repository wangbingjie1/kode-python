"""修复 ontology_tools.py - 删除残留的废弃函数体"""

file_path = r"e:\AI\AI ERP\kode-python\kode\tools\ontology_tools.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到275行开始的残留代码（第一个残留）
# 找到365行开始的残留代码（第二个残留）
# 删除这些行直到遇到下一个有效的函数定义

output_lines = []
skip_mode = False
skip_indent = None

for i, line in enumerate(lines, start=1):
    stripped = line.strip()

    # 检测残留代码的开始（异常的参数行）
    if i == 275 and "self, schema_metadata" in line and "def " not in line:
        print(f"Found residue 1 at line {i}, skipping until next function...")
        skip_mode = True
        skip_indent = 4  # 类方法缩进
        continue

    if i == 365 and "self, schema_metadata" in line and "def " not in line:
        print(f"Found residue 2 at line {i}, skipping until next function...")
        skip_mode = True
        skip_indent = 4
        continue

    if skip_mode:
        # 检查是否遇到下一个函数定义（同级缩进的 def）
        if stripped:
            current_indent = len(line) - len(line.lstrip())
            if ("def " in line or "async def " in line or "class " in line) and current_indent == skip_indent:
                print(f"Found next function at line {i}, resuming normal mode")
                skip_mode = False
                skip_indent = None
                output_lines.append(line)
        # else: 跳过空行
    else:
        output_lines.append(line)

# 写回
with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(output_lines)

print(f"Cleanup complete! Removed residual code from line 275 and 365")
