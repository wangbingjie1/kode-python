import json

with open('ontology_store/yanfa/ontology_latest.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

uncertainties = data.get('ontology', {}).get('uncertainties', [])

# 提取高优先级（impact=high 或 confidence=high）
high_priority = []
for i, u in enumerate(uncertainties):
    impact = u.get('impact', '')
    confidence = u.get('confidence', '')
    if impact == 'high' or confidence == 'high':
        u['index'] = i
        high_priority.append(u)

print(f"总不确定项: {len(uncertainties)}")
print(f"高优先级不确定项: {len(high_priority)}\n")

# 打印前15个
for item in high_priority[:15]:
    print(f"[{item['index']}] {item.get('type', 'unknown')}: {item.get('description', '')}")
    print(f"   影响: {item.get('impact', 'N/A')} | 置信度: {item.get('confidence', 'N/A')}")
    if 'questions' in item:
        for q in item['questions']:
            print(f"   - {q}")
    print()
