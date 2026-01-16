# Trantor - 智能数据分析平台

> Transform data into insights, let AI be your Chief Analyst
> 将数据转化为洞察，让 AI 成为你的首席分析师

Trantor 是一个企业级数据分析平台，通过 AI 驱动的知识图谱构建，帮助业务用户理解、分析和可视化数据。

## 功能特性

### 知识图谱/本体构建
- 可视化知识图谱编辑器，支持拖放交互
- 7 种对象类型：DataSet、Analysis、Report、MLModel、UserCohort、MarketingCampaign、StrategyPlaybook
- 6 种关系类型：USES_DATA、TRAINS_MODEL、GENERATES_REPORT 等
- 4 层级架构：数据层 → 分析层 → 报告/模型层 → 策略层

### ETL 数据工作流
- 数据摄入界面
- 数据清洗工作流
- 智能问卷系统：自动识别数据中的歧义并提出问题
- 支持多种数据源接入

### AI 驱动分析
- 对话式 AI 助手
- 自动问卷解答（AI Agent）
- 智能建议引擎
- 本体版本管理和升级

### BI 仪表板
- 多种仪表板模板（分析、监控、报告等）
- 实时数据监控
- 可交互的图表和图形
- 销售漏斗、目标追踪等

### 项目管理
- 多项目支持（E-commerce、SaaS、Marketing 等）
- 项目收藏和状态跟踪
- 最近访问项目追踪

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Next.js 15 (App Router) |
| 前端 | React 19, TypeScript |
| UI 组件 | shadcn/ui, Radix UI |
| 样式 | Tailwind CSS 4 |
| 数据可视化 | D3.js, Recharts |
| 状态管理 | Zustand |
| 表单处理 | React Hook Form, Zod |
| 图标 | Lucide React |

## 项目结构

```
tractor-v1/
├── app/                          # Next.js App Router
│   ├── (dashboard)/              # 仪表板路由组
│   │   ├── bi-dashboard/         # BI 仪表板
│   │   ├── dashboard/            # 主仪表板（知识图谱）
│   │   ├── data-cleaning/        # 数据清洗
│   │   └── data-ingestion/       # 数据摄入
│   └── (public)/                 # 公开页面（登录页）
├── components/                   # React 组件
│   ├── ui/                       # shadcn/ui 基础组件
│   ├── knowledge-universe/       # 知识图谱组件
│   ├── layout/                   # 布局组件
│   └── modals/                   # 模态框组件
├── lib/                          # 工具库和数据
│   ├── auth-context.tsx          # 认证上下文
│   ├── project-store.ts          # 项目状态管理
│   └── utils.ts                  # 工具函数
├── hooks/                        # 自定义 Hooks
├── types/                        # TypeScript 类型定义
└── public/                       # 静态资源
```

## 快速开始

### 环境要求

- Node.js 18.0 或更高版本
- npm / yarn / pnpm

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd tractor-v1

# 安装依赖
npm install
# 或
yarn install
# 或
pnpm install
```

### 开发

```bash
# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

### 构建

```bash
# 生产构建
npm run build

# 启动生产服务器
npm run start
```

### 代码检查

```bash
npm run lint
```

## 主要页面

| 路径 | 说明 |
|------|------|
| `/` | 登录页/产品介绍 |
| `/dashboard` | 知识图谱主仪表板 |
| `/data-ingestion` | 数据摄入 |
| `/data-cleaning` | 数据清洗工作流 |
| `/bi-dashboard` | BI 可视化仪表板 |

## 开发指南

### 添加新组件

项目使用 shadcn/ui 组件库，添加新组件：

```bash
npx shadcn@latest add <component-name>
```

### 样式约定

- 使用 Tailwind CSS 进行样式开发
- 遵循 shadcn/ui 的 New York 风格
- 支持暗色模式（通过 next-themes）

### 状态管理

项目使用 Zustand 进行状态管理，主要状态存储在：
- `lib/project-store.ts` - 项目数据管理
- `lib/auth-context.tsx` - 认证状态

### 类型定义

所有 TypeScript 类型定义位于 `types/` 目录：
- `ontology.ts` - 本体/知识图谱类型
- `knowledge-universe.ts` - 知识宇宙类型
- `pending-questions.ts` - 待处理问题类型

## 许可证

Private - All Rights Reserved
