"""
重构领域结构：将不确定性和规则整合到各个领域文件中
"""
import json
from pathlib import Path
from typing import Dict, List, Any

def load_uncertainties() -> Dict[str, List[Dict]]:
    """加载不确定性文件，按领域分组"""
    uncertainties_file = Path("schema_store/yanfa/uncertainties.json")
    with open(uncertainties_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 按领域分组
    domain_uncertainties = {}
    for domain_result in data.get('domain_results', []):
        domain_name = domain_result['domain_name']
        uncertainties = domain_result.get('uncertainties', [])
        if uncertainties:
            domain_uncertainties[domain_name] = uncertainties

    return domain_uncertainties

def load_rules(domain_name: str) -> List[str]:
    """加载领域规则文件"""
    rules_file = Path(f"schema_store/yanfa/domains/{domain_name}_rules.txt")
    if not rules_file.exists():
        return []

    with open(rules_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析规则文件（简单的文本处理）
    rules = []
    current_rule = {}

    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('## 规则'):
            if current_rule:
                rules.append(current_rule)
            current_rule = {'title': line}
        elif line.startswith('**'):
            key = line.split(':')[0].replace('**', '').strip()
            value = ':'.join(line.split(':')[1:]).strip() if ':' in line else ''
            current_rule[key] = value

    if current_rule:
        rules.append(current_rule)

    return rules

def update_domain_file(domain_file: Path, uncertainties: List[Dict], rules: List[Any]):
    """更新领域文件，添加不确定性和规则"""
    with open(domain_file, 'r', encoding='utf-8') as f:
        domain_data = json.load(f)

    # 添加不确定性
    if uncertainties:
        domain_data['uncertainties'] = uncertainties

    # 添加规则
    if rules:
        domain_data['business_rules'] = rules

    # 保存更新后的文件
    with open(domain_file, 'w', encoding='utf-8') as f:
        json.dump(domain_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] 更新 {domain_file.name}: {len(uncertainties)} 个不确定性, {len(rules)} 条规则")

def main():
    """主函数"""
    print("[START] 开始重构领域结构...")

    # 1. 加载所有不确定性
    print("\n[LOAD] 加载不确定性数据...")
    domain_uncertainties = load_uncertainties()
    print(f"找到 {len(domain_uncertainties)} 个领域的不确定性")

    # 2. 遍历所有领域文件
    domains_dir = Path("schema_store/yanfa/domains")
    domain_files = list(domains_dir.glob("*.json"))

    print(f"\n[FILES] 找到 {len(domain_files)} 个领域文件")

    for domain_file in domain_files:
        domain_name = domain_file.stem

        # 获取不确定性（需要匹配名称）
        uncertainties = []
        for key in domain_uncertainties.keys():
            if key.replace('_', '') in domain_name.replace('_', '') or \
               domain_name.replace('_', '') in key.replace('_', ''):
                uncertainties = domain_uncertainties[key]
                break

        # 获取规则
        rules = load_rules(domain_name)

        # 更新文件
        if uncertainties or rules:
            update_domain_file(domain_file, uncertainties, rules)

    print("\n✅ 重构完成！")
    print("\n下一步：删除冗余文件")
    print("  - schema_store/yanfa/uncertainties.json")
    print("  - schema_store/yanfa/domains/*_rules.txt")

if __name__ == "__main__":
    main()
