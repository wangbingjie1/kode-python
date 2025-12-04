<!--
Sync Impact Report:
- Version change: N/A → 1.0.0 (Initial ratification)
- Modified principles: N/A (Initial creation)
- Added sections: All core principles and governance rules established
- Removed sections: N/A
- Templates requiring updates:
  ✅ plan-template.md - Verified constitution check section aligns
  ✅ spec-template.md - Verified requirements and success criteria alignment
  ✅ tasks-template.md - Verified task categorization reflects principles
- Follow-up TODOs: None
-->

# Kode 项目宪章

## 核心原则

### I. 质量至上（非妥协项）

**声明**：代码质量和可靠性是首要目标，速度和便利性必须服从于质量。

**规则**：
- 所有代码 MUST 经过测试验证后才能提交给用户
- 不允许降级方案（fallback/degradation）- 要么正确实现，要么不实现
- 不确定的方案 MUST NOT 推荐给用户 - 只提供经过验证的最可靠方案
- 用户有选择困难症 - 可以提问但 MUST NOT 提供多个选项，直接给出最佳方案

**理由**：项目面向生产环境的 ERP 数据分析，错误分析可能导致业务决策失误，代价高昂。质量缺陷的成本远高于开发速度的延迟。

### II. 第一性原理思维

**声明**：解决问题必须回归本质，而非堆砌解决方案或模仿现有实现。

**规则**：
- 遇到问题时 MUST 先分析根本原因（root cause），而非症状
- 架构决策 MUST 基于实际需求推导，而非"业界最佳实践"的盲目套用
- 技术选型 MUST 有明确的工程理由，不得因"流行"或"新颖"而采用

**理由**：过度工程和不必要的抽象是软件复杂度的主要来源。从第一性原理出发可以避免 90% 的架构过度设计。

### III. 批判性思维

**声明**：所有需求、方案和实现都必须接受批判性审视。

**规则**：
- 用户需求 MUST 经过质疑和澄清 - 表面需求可能不是真实需求
- 自己的解决方案 MUST 经过反思 - "这个方案真的解决了问题吗？有没有更简单的方式？"
- 依赖引入 MUST 经过权衡 - "这个库真的必要吗？自己实现的成本是否可接受？"

**理由**：盲目接受需求和方案会导致无效开发和技术债务累积。批判性思维是保持代码库健康的免疫系统。

### IV. 测试驱动开发（TDD）

**声明**：代码必须先通过测试验证，再交付给用户。

**规则**：
- 新功能 MUST 先编写测试用例
- 测试用例 MUST 在实现前失败（红），实现后通过（绿）
- 修复 bug MUST 先写回归测试，验证 bug 存在，修复后测试通过
- 交付前 MUST 运行完整测试套件并全部通过

**理由**：用户依赖我们的数据分析结果做业务决策，未经测试的代码等同于不可靠的决策依据。TDD 是质量的底线保证。

### V. 简化优先（YAGNI）

**声明**：避免过度工程，只实现当前需要的功能。

**规则**：
- MUST NOT 为"未来可能的需求"提前设计
- MUST NOT 添加超出需求范围的功能或抽象
- 三次重复前 MUST NOT 提取抽象（Rule of Three）
- 删除未使用的代码 - 不允许"以防万一"的保留代码

**理由**：项目已经从多 Agent 架构简化为单 Agent 架构，从通用 CLI 工具简化为专注数据分析的 Web 服务。这些简化带来了 30% 的 token 节省和显著的维护成本降低。过度工程是项目失控的主要原因。

### VI. 领域专注

**声明**：Kode 专注于 ERP 数据分析场景，不做通用编程助手。

**规则**：
- 工具集 MUST 围绕数据分析场景设计（数据库、本体、可视化、交互）
- MUST NOT 添加文件操作工具（FileRead/FileWrite/FileEdit）- 数据分析不需要
- MUST NOT 添加通用系统工具（Bash/Grep/Glob）- 有更专用的替代方案
- 新工具 MUST 有明确的数据分析用例

**理由**：专注带来深度。通用助手无法在任何领域做到最优，而专注的工具可以在特定领域提供 10 倍更好的体验。

## 架构约束

### 单一 Agent 架构

**规则**：
- 系统 MUST 使用唯一的 `data-analyst` Agent
- MUST NOT 创建多个 Agent 或 Agent 加载系统
- Agent MUST 优先使用已缓存的 schema 和 ontology，避免重复构建

**理由**：多 Agent 系统带来的复杂度远超其收益。单 Agent + 智能工具选择已足够应对数据分析场景。

### 5 层架构分离

**规则**：
- Core Layer (核心): LLM 管理、权限系统
- Tools Layer (工具): 数据分析专用工具集
- Agents Layer (智能体): 单一 data-analyst Agent
- Services Layer (服务): 业务逻辑和数据库管理
- Web Layer (Web): FastAPI REST/SSE 端点

各层 MUST NOT 跨层调用（如 Web 直接调用 Core，跳过 Services）。

**理由**：清晰的层次边界防止依赖混乱，便于测试和维护。

### 数据库迁移强制

**规则**：
- Schema 变更 MUST 生成 Alembic 迁移文件
- MUST NOT 手动修改数据库结构
- 迁移 MUST 包含 upgrade 和 downgrade 路径

**理由**：多环境部署（开发/测试/生产）需要可重复的数据库演进过程。手动变更会导致环境不一致。

## 开发流程

### 中文优先

**规则**：
- 代码注释、文档、commit message MUST 使用中文
- 函数/变量名使用英文（遵循 Python/TypeScript 惯例）
- 用户交互 MUST 使用中文

**理由**：团队主要为中文用户，中文表达更准确，降低沟通成本。

### 文档最小化

**规则**：
- MUST NOT 主动生成说明文档（README/API 文档）- 除非用户明确要求
- 文档生成后 MUST 放在 `doc/` 目录
- 代码 SHOULD 自解释 - 优先写清晰的代码而非冗长的注释

**理由**：用户明确表示"不会看你的文档"。过度文档化是浪费时间，代码即文档。

### 测试代码隔离

**规则**：
- 测试代码 MUST 放在 `test/` 或 `tests/` 目录
- MUST NOT 在生产代码中混入测试逻辑

## 治理规则

**宪章优先级**：本宪章是项目的最高准则，所有开发实践、代码审查、架构决策必须符合本宪章。

**修订流程**：
1. 提出修订的工程理由（不得因"方便"或"流行"而修改原则）
2. 评估修订对现有代码的影响范围
3. 制定迁移计划（如有破坏性变更）
4. 更新相关模板和文档
5. 执行版本号升级（语义化版本）

**合规性审查**：
- 所有 PR MUST 通过宪章合规检查
- 违反原则的代码 MUST 提供书面豁免理由
- 复杂度违规 MUST 在 plan.md 的 Complexity Tracking 表中记录

**版本控制**：
- MAJOR 版本：移除或重新定义核心原则（破坏性变更）
- MINOR 版本：新增原则或扩展现有指导
- PATCH 版本：澄清措辞、修正歧义、非语义改动

**指导文档**：运行时开发指导参见 [CLAUDE.md](../../CLAUDE.md)。

---

**Version**: 1.0.0 | **Ratified**: 2025-12-04 | **Last Amended**: 2025-12-04
