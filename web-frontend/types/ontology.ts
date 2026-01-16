// types/ontology.ts

// ============ 节点类型枚举 ============

// 原有 Mock 数据类型（营销分析场景）
export type MockObjectType =
  | 'DataSet'
  | 'Analysis'
  | 'Report'
  | 'MLModel'
  | 'UserCohort'
  | 'MarketingCampaign'
  | 'StrategyPlaybook';

// 真实本体类型（ERP 数据库场景）
export type RealObjectType =
  | 'Domain'           // 业务域
  | 'Entity'           // 通用实体
  | 'User'             // 用户相关实体
  | 'Order'            // 订单相关实体
  | 'Product'          // 产品相关实体
  | 'Config'           // 配置/设置实体
  | 'Log'              // 日志/记录实体
  | 'AbstractEntity'   // 抽象实体
  | 'Metric'           // 业务指标
  | 'BusinessRule';    // 业务规则

// 统一对象类型（支持两种场景）
export type ObjectType = MockObjectType | RealObjectType;

// ============ 关系类型枚举 ============

// 原有 Mock 数据关系类型
export type MockRelationType =
  | 'USES_DATA'
  | 'TRAINS_MODEL'
  | 'GENERATES_REPORT'
  | 'INFORMS_STRATEGY'
  | 'TARGETS_COHORT'
  | 'AFFECTS_CAMPAIGN';

// 真实本体关系类型（数据库关系）
export type RealRelationType =
  | 'HAS_ONE'          // 一对一关系
  | 'HAS_MANY'         // 一对多关系
  | 'BELONGS_TO'       // 从属关系
  | 'CONTAINS'         // 域包含实体
  | 'APPLIES_TO';      // 规则应用到实体

// 统一关系类型
export type RelationType = MockRelationType | RealRelationType;

// ============ 本体节点定义 ============

export interface OntologyNode {
  id: string;
  label?: string;                    // 显示标签（真实本体使用）
  type: ObjectType;
  domain?: string;                   // 所属业务域（真实本体使用）
  properties: {
    [key: string]: string | number | boolean | string[] | undefined;
  };
  // 用于可视化的额外属性
  level?: number;                    // 层级
  position?: { x: number; y: number };
  visible?: boolean;
}

// ============ 本体关系定义 ============

export interface OntologyRelation {
  id?: string;
  source: string;
  target: string;
  type: RelationType;
  properties?: {
    [key: string]: string | number | boolean | undefined;
  };
  visible?: boolean;
}

// ============ API 响应类型 ============

export interface OntologyVisualizationResponse {
  nodes: OntologyNode[];
  relations: OntologyRelation[];
  meta: {
    ontology_name?: string;
    product_name?: string;
    business_model?: string;
    created_at?: string;
    source_connection?: string;
    version?: string;
  };
  statistics: {
    total_nodes: number;
    total_relations: number;
    domain_count?: number;
    class_count?: number;
    rule_count?: number;
    metric_count?: number;
    [key: string]: number | undefined;
  };
}

export interface OntologyDomain {
  id: string;
  name: string;
  label: string;
  class_count: number;
}

// ============ 层级定义 ============

// Mock 数据层级
export const MockNodeLevels: Record<MockObjectType, number> = {
  'DataSet': 1,
  'Analysis': 2,
  'MLModel': 2,
  'Report': 3,
  'UserCohort': 3,
  'MarketingCampaign': 4,
  'StrategyPlaybook': 4
};

// 真实本体层级
export const RealNodeLevels: Record<RealObjectType, number> = {
  'Domain': 0,
  'Entity': 1,
  'User': 1,
  'Order': 1,
  'Product': 1,
  'Config': 2,
  'Log': 2,
  'AbstractEntity': 1,
  'Metric': 3,
  'BusinessRule': 3
};

// 统一层级获取函数
export function getNodeLevel(type: ObjectType): number {
  if (type in MockNodeLevels) {
    return MockNodeLevels[type as MockObjectType];
  }
  if (type in RealNodeLevels) {
    return RealNodeLevels[type as RealObjectType];
  }
  return 1;
}

// ============ 节点颜色配置 ============

// Mock 数据颜色
export const MockNodeColors: Record<MockObjectType, { bg: string; border: string; text: string }> = {
  'DataSet': { bg: '#E8F5F1', border: '#A8D5BA', text: '#2C7A59' },
  'Analysis': { bg: '#FEF3E2', border: '#F4E4C1', text: '#92400E' },
  'Report': { bg: '#F3E8FF', border: '#C9B6E4', text: '#6B21A8' },
  'MLModel': { bg: '#E0F2FE', border: '#7AB8CC', text: '#0C4A6E' },
  'UserCohort': { bg: '#FEE2E2', border: '#F5CAC3', text: '#991B1B' },
  'MarketingCampaign': { bg: '#FFF7ED', border: '#FED7AA', text: '#9A3412' },
  'StrategyPlaybook': { bg: '#F0F9FF', border: '#BAE6FD', text: '#075985' }
};

// 真实本体颜色
export const RealNodeColors: Record<RealObjectType, { bg: string; border: string; text: string }> = {
  'Domain': { bg: '#F3E8FF', border: '#C084FC', text: '#7C3AED' },
  'Entity': { bg: '#F1F5F9', border: '#94A3B8', text: '#475569' },
  'User': { bg: '#DBEAFE', border: '#60A5FA', text: '#1D4ED8' },
  'Order': { bg: '#FEF3C7', border: '#FBBF24', text: '#B45309' },
  'Product': { bg: '#D1FAE5', border: '#34D399', text: '#059669' },
  'Config': { bg: '#E0E7FF', border: '#A5B4FC', text: '#4338CA' },
  'Log': { bg: '#FEE2E2', border: '#FCA5A5', text: '#DC2626' },
  'AbstractEntity': { bg: '#F5F5F4', border: '#A8A29E', text: '#57534E' },
  'Metric': { bg: '#CFFAFE', border: '#22D3EE', text: '#0891B2' },
  'BusinessRule': { bg: '#FCE7F3', border: '#F472B6', text: '#DB2777' }
};

// 统一颜色获取函数
export function getNodeColors(type: ObjectType): { bg: string; border: string; text: string } {
  if (type in MockNodeColors) {
    return MockNodeColors[type as MockObjectType];
  }
  if (type in RealNodeColors) {
    return RealNodeColors[type as RealObjectType];
  }
  return { bg: '#F1F5F9', border: '#94A3B8', text: '#475569' };
}

// ============ 关系颜色配置 ============

// Mock 数据关系颜色
export const MockRelationColors: Record<MockRelationType, string> = {
  'USES_DATA': '#A8D5BA',
  'TRAINS_MODEL': '#7AB8CC',
  'GENERATES_REPORT': '#C9B6E4',
  'INFORMS_STRATEGY': '#F4E4C1',
  'TARGETS_COHORT': '#F5CAC3',
  'AFFECTS_CAMPAIGN': '#FED7AA'
};

// 真实本体关系颜色
export const RealRelationColors: Record<RealRelationType, string> = {
  'HAS_ONE': '#60A5FA',
  'HAS_MANY': '#34D399',
  'BELONGS_TO': '#F472B6',
  'CONTAINS': '#C084FC',
  'APPLIES_TO': '#FBBF24'
};

// 统一关系颜色获取函数
export function getRelationColor(type: RelationType): string {
  if (type in MockRelationColors) {
    return MockRelationColors[type as MockRelationType];
  }
  if (type in RealRelationColors) {
    return RealRelationColors[type as RealRelationType];
  }
  return '#94A3B8';
}

// ============ 兼容性导出（保持向后兼容）============

export const NodeLevels = MockNodeLevels;
export const NodeColors = MockNodeColors;
export const RelationColors = MockRelationColors;
