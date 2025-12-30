"""
本体文件迁移脚本

将现有的 ontology_v1.json 和 ontology_v3.json 重命名为 ontology.json
"""

import sys
import io
from pathlib import Path
import shutil
import json
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def migrate_ontology_files(base_path: str = "./ontology_store"):
    """
    迁移所有本体文件到新的命名方式

    Args:
        base_path: 本体存储根目录
    """
    base = Path(base_path)
    if not base.exists():
        print(f"❌ 本体存储目录不存在: {base}")
        return

    migrated_count = 0
    skipped_count = 0
    backup_dir = base / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 遍历所有可能的本体文件
    v3_files = list(base.glob("*/ontology_v3.json")) + list(base.glob("*/*/ontology_v3.json"))
    v1_files = list(base.glob("*/ontology_v1.json")) + list(base.glob("*/*/ontology_v1.json"))

    # 处理 v3 文件（优先级最高）
    for v3_file in v3_files:
        target_file = v3_file.parent / "ontology.json"

        if target_file.exists():
            print(f"⏭️  跳过（目标已存在）: {v3_file}")
            skipped_count += 1
            continue

        # 创建备份
        backup_path = backup_dir / v3_file.relative_to(base)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(v3_file, backup_path)

        # 重命名
        v3_file.rename(target_file)
        print(f"✅ 迁移: {v3_file} → {target_file}")
        migrated_count += 1

        # 删除同目录下的 v1 文件（如果存在）
        v1_in_same_dir = v3_file.parent / "ontology_v1.json"
        if v1_in_same_dir.exists():
            v1_backup = backup_dir / v1_in_same_dir.relative_to(base)
            v1_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(v1_in_same_dir, v1_backup)
            v1_in_same_dir.unlink()
            print(f"🗑️  删除旧版本: {v1_in_same_dir}")

    # 处理剩余的 v1 文件（只有在没有 v3 的情况下才迁移）
    for v1_file in v1_files:
        v3_in_same_dir = v1_file.parent / "ontology_v3.json"
        target_file = v1_file.parent / "ontology.json"

        # 如果同目录有 v3 或目标已存在，跳过
        if v3_in_same_dir.exists() or target_file.exists():
            print(f"⏭️  跳过（已被 v3 替代或目标已存在）: {v1_file}")
            skipped_count += 1
            continue

        # 创建备份
        backup_path = backup_dir / v1_file.relative_to(base)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(v1_file, backup_path)

        # 重命名
        v1_file.rename(target_file)
        print(f"✅ 迁移 (v1): {v1_file} → {target_file}")
        migrated_count += 1

    # 输出统计
    print(f"\n{'='*60}")
    print(f"迁移完成！")
    print(f"  ✅ 成功迁移: {migrated_count} 个文件")
    print(f"  ⏭️  跳过: {skipped_count} 个文件")
    if migrated_count > 0:
        print(f"  💾 备份目录: {backup_dir}")
    print(f"{'='*60}")


def verify_migration(base_path: str = "./ontology_store"):
    """
    验证迁移结果

    Args:
        base_path: 本体存储根目录
    """
    base = Path(base_path)
    if not base.exists():
        print(f"❌ 本体存储目录不存在: {base}")
        return

    print("\n验证迁移结果...")

    # 检查是否还有旧文件
    v3_files = list(base.glob("*/ontology_v3.json")) + list(base.glob("*/*/ontology_v3.json"))
    v1_files = list(base.glob("*/ontology_v1.json")) + list(base.glob("*/*/ontology_v1.json"))
    new_files = list(base.glob("*/ontology.json")) + list(base.glob("*/*/ontology.json"))

    print(f"  📁 新格式文件 (ontology.json): {len(new_files)}")
    print(f"  📁 遗留 v3 文件: {len(v3_files)}")
    print(f"  📁 遗留 v1 文件: {len(v1_files)}")

    if v3_files or v1_files:
        print("\n⚠️  仍有遗留的旧版本文件，可能需要手动处理：")
        for f in v3_files + v1_files:
            print(f"    - {f}")
    else:
        print("\n✅ 所有文件已成功迁移！")


if __name__ == "__main__":
    import sys

    base_path = sys.argv[1] if len(sys.argv) > 1 else "./ontology_store"

    print(f"开始迁移本体文件...")
    print(f"基础路径: {base_path}")
    print()

    migrate_ontology_files(base_path)
    verify_migration(base_path)

    print("\n✅ 迁移脚本执行完成！")
    print("💡 如果一切正常，可以手动删除备份目录。")
