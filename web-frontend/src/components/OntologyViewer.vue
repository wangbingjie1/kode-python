<template>
  <div class="ontology-viewer">
    <div class="ontology-header">
      <h2>业务本体</h2>
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索实体、属性..."
          @input="onSearchInput"
        />
        <button @click="search" class="btn-search">搜索</button>
      </div>
    </div>

    <div class="ontology-content">
      <!-- Ontology list sidebar -->
      <div class="ontology-list">
        <h3>已保存的本体</h3>
        <div
          v-for="ontology in ontologies"
          :key="ontology.connection_name"
          :class="['ontology-item', { active: selectedOntology?.connection_name === ontology.connection_name }]"
          @click="selectOntology(ontology.connection_name)"
        >
          <div class="ontology-name">{{ ontology.connection_name }}</div>
          <div class="ontology-meta">
            个实体: {{ ontology.concept_count }} · {{ ontology.relationship_count }} 个关系
          </div>
          <div class="ontology-date">{{ formatDate(ontology.created_at) }}</div>
        </div>
        <div v-if="ontologies.length === 0" class="empty-state">
          暂无保存的本体
        </div>
      </div>

      <!-- Ontology details -->
      <div class="ontology-details">
        <div v-if="!selectedOntology" class="empty-selection">
          <p>请选择一个本体查看详情</p>
        </div>

        <div v-else>
          <div class="ontology-info">
            <h3>{{ selectedOntology.connection_name }}</h3>
            <p>版本: {{ selectedOntology.version }}</p>
            <p>创建时间: {{ formatDate(selectedOntology.created_at) }}</p>
            <p>概念: {{ selectedOntology.ontology?.concepts ? Object.keys(selectedOntology.ontology.concepts).length : 0 }} |
               属性: {{ selectedOntology.ontology?.properties ? Object.keys(selectedOntology.ontology.properties).length : 0 }} |
               关系: {{ selectedOntology.ontology?.relationships?.length || 0 }}</p>
          </div>

          <!-- Search results -->
          <div v-if="searchResults.length > 0" class="search-results">
            <h4>搜索结果 ({{ searchResults.length }})</h4>
            <div
              v-for="(result, idx) in searchResults"
              :key="idx"
              class="search-result-item"
            >
              <div class="result-header">
                <span class="entity-type">{{ result.entity.type }}</span>
                <span class="entity-name">{{ result.entity.name }}</span>
                <span class="result-score">相关度: {{ result.score.toFixed(2) }}</span>
              </div>
              <div v-if="result.entity.description" class="result-description">
                {{ result.entity.description }}
              </div>
              <div class="result-meta">
                <span v-if="result.entity.source_table"
                  >来源表: {{ result.entity.source_table }}</span
                >
                <span v-if="result.entity.source_column"
                  >来源列: {{ result.entity.source_column }}</span
                >
              </div>
            </div>
          </div>

          <!-- Entities view -->
          <div v-else class="entities-section">
            <div class="section-tabs">
              <button
                :class="['tab', { active: currentTab === 'entities' }]"
                @click="currentTab = 'entities'"
              >
                概念 ({{ selectedOntology.ontology?.concepts ? Object.keys(selectedOntology.ontology.concepts).length : 0 }})
              </button>
              <button
                :class="['tab', { active: currentTab === 'relationships' }]"
                @click="currentTab = 'relationships'"
              >
                关系 ({{ selectedOntology.ontology?.relationships?.length || 0 }})
              </button>
              <button
                :class="['tab', { active: currentTab === 'graph' }]"
                @click="currentTab = 'graph'"
              >
                关系图
              </button>
            </div>

            <div class="tab-content">
              <!-- Entities tab -->
              <div v-if="currentTab === 'entities'" class="entities-list">
                <div
                  v-for="entity in filteredEntities"
                  :key="entity.name"
                  class="entity-card"
                >
                  <div class="entity-header">
                    <span class="entity-type-badge">{{ entity.type }}</span>
                    <h4>{{ entity.name }}</h4>
                  </div>
                  <p v-if="entity.description" class="entity-description">
                    {{ entity.description }}
                  </p>
                  <div class="entity-source">
                    <span v-if="entity.source_table">表: {{ entity.source_table }}</span>
                    <span v-if="entity.source_column">列: {{ entity.source_column }}</span>
                  </div>
                </div>
              </div>

              <!-- Relationships tab -->
              <div v-if="currentTab === 'relationships'" class="relationships-list">
                <div
                  v-for="(rel, idx) in selectedOntology.ontology?.relationships || []"
                  :key="idx"
                  class="relationship-card"
                >
                  <div class="relationship-flow">
                    <span class="entity-node">{{ rel.source_concept }}</span>
                    <span class="relationship-arrow">
                      <span class="relationship-type">{{ rel.relationship_type }}</span>
                      →
                    </span>
                    <span class="entity-node">{{ rel.target_concept }}</span>
                  </div>
                  <div v-if="rel.strength" class="relationship-meta">
                    强度: {{ rel.strength }}
                  </div>
                  <p v-if="rel.description" class="relationship-description">
                    {{ rel.description }}
                  </p>
                </div>
              </div>

              <!-- Graph tab -->
              <div v-if="currentTab === 'graph'" class="graph-view">
                <div class="graph-controls">
                  <div class="control-group">
                    <label>布局算法:</label>
                    <select v-model="graphLayout" @change="updateGraph">
                      <option value="force">力导向布局</option>
                      <option value="circular">环形布局</option>
                    </select>
                  </div>
                  <div class="control-group">
                    <label>节点大小:</label>
                    <input
                      v-model.number="nodeSize"
                      type="range"
                      min="20"
                      max="80"
                      @input="updateGraph"
                    />
                    <span>{{ nodeSize }}</span>
                  </div>
                  <div class="control-group">
                    <label>显示标签</label>
                    <input v-model="showLabels" type="checkbox" @change="updateGraph" />
                  </div>
                </div>
                <v-chart
                  ref="graphChart"
                  :option="graphOption"
                  :autoresize="true"
                  class="graph-chart"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { listOntologies, getOntology, searchOntology } from '@/services/api'
import { notification } from '@/composables/useNotification'
import { use } from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

// 注册 ECharts 组件
use([GraphChart, TooltipComponent, LegendComponent, CanvasRenderer])

const ontologies = ref<any[]>([])
const selectedOntology = ref<any | null>(null)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const currentTab = ref<'entities' | 'relationships' | 'graph'>('entities')

// 图表配置
const graphChart = ref<InstanceType<typeof VChart> | null>(null)
const graphLayout = ref<'force' | 'circular'>('force')
const nodeSize = ref(40)
const showLabels = ref(true)
const graphOption = ref<any>({})

onMounted(async () => {
  await loadOntologies()
})

async function loadOntologies() {
  try {
    ontologies.value = await listOntologies()
  } catch (error: any) {
    notification.error('加载失败', error.message)
  }
}

async function selectOntology(name: string) {
  try {
    selectedOntology.value = await getOntology(name)
    searchResults.value = []
    searchQuery.value = ''
    currentTab.value = 'entities'
    updateGraph()
  } catch (error: any) {
    notification.error('加载失败', error.message)
  }
}

// 构建图表数据
function buildGraphData() {
  if (!selectedOntology.value?.ontology) {
    return { nodes: [], links: [], categories: [] }
  }

  const concepts = selectedOntology.value.ontology.concepts || {}
  const relationships = selectedOntology.value.ontology.relationships || []

  // 按领域分组
  const domainColors: Record<string, string> = {
    user_management: '#5470c6',
    content_management: '#91cc75',
    interaction_management: '#fac858',
    payment_management: '#ee6666',
    notification_management: '#73c0de',
    system_management: '#3ba272',
    analytics_management: '#fc8452',
    default: '#9a60b4'
  }

  const domains = new Set<string>()
  const nodes = Object.entries(concepts).map(([key, concept]: [string, any]) => {
    const domain = concept.domain || 'default'
    domains.add(domain)
    return {
      id: key,
      name: concept.business_name_cn || concept.technical_name || key,
      symbolSize: nodeSize.value,
      category: domain,
      value: concept.importance === 'high' ? 3 : concept.importance === 'medium' ? 2 : 1,
      label: {
        show: showLabels.value,
        fontSize: 11
      },
      itemStyle: {
        color: domainColors[domain] || domainColors.default
      }
    }
  })

  const links = relationships.map((rel: any) => ({
    source: rel.source_concept,
    target: rel.target_concept,
    label: {
      show: false,
      formatter: rel.relationship_type
    },
    lineStyle: {
      curveness: 0.2,
      width: rel.strength === 'strong' ? 2 : 1
    }
  }))

  const categories = Array.from(domains).map((domain) => ({
    name: domain
  }))

  return { nodes, links, categories }
}

// 更新图表
function updateGraph() {
  const { nodes, links, categories } = buildGraphData()

  graphOption.value = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `<b>${params.name}</b><br/>领域: ${params.data.category}<br/>重要性: ${params.data.value}`
        } else if (params.dataType === 'edge') {
          return `${params.data.source} → ${params.data.target}`
        }
        return ''
      }
    },
    legend: {
      data: categories.map((c) => c.name),
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      textStyle: {
        fontSize: 12
      }
    },
    series: [
      {
        type: 'graph',
        layout: graphLayout.value,
        data: nodes,
        links: links,
        categories: categories,
        roam: true,
        label: {
          position: 'right',
          formatter: '{b}'
        },
        labelLayout: {
          hideOverlap: true
        },
        scaleLimit: {
          min: 0.4,
          max: 2
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 3
          }
        },
        force:
          graphLayout.value === 'force'
            ? {
                repulsion: 400,
                gravity: 0.1,
                edgeLength: [100, 200],
                layoutAnimation: true
              }
            : undefined
      }
    ]
  }
}

// 监听选中本体变化
watch(selectedOntology, () => {
  if (selectedOntology.value) {
    updateGraph()
  }
})

async function search() {
  if (!selectedOntology.value || !searchQuery.value.trim()) {
    searchResults.value = []
    return
  }

  try {
    const results = await searchOntology(selectedOntology.value.connection_name, {
      query: searchQuery.value,
      limit: 20
    })
    searchResults.value = results
  } catch (error: any) {
    notification.error('搜索失败', error.message)
  }
}

function onSearchInput() {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
  }
}

const filteredEntities = computed(() => {
  if (!selectedOntology.value?.ontology?.concepts) return []
  // 将 concepts 对象转换为数组
  return Object.entries(selectedOntology.value.ontology.concepts).map(([key, concept]: [string, any]) => ({
    id: key,
    name: concept.business_name_cn || concept.technical_name || key,
    type: concept.domain || 'concept',
    description: concept.description,
    source_table: concept.data_source,
    source_column: concept.technical_name
  }))
})

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.ontology-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.ontology-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.ontology-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.search-box {
  display: flex;
  gap: 0.5rem;
}

.search-box input {
  padding: 0.5rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  width: 300px;
  font-size: 0.875rem;
}

.btn-search {
  padding: 0.5rem 1rem;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-search:hover {
  background: #1976d2;
}

.ontology-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.ontology-list {
  width: 300px;
  background: white;
  border-right: 1px solid #e0e0e0;
  overflow-y: auto;
  padding: 1rem;
}

.ontology-list h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: #666;
}

.ontology-item {
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.ontology-item:hover {
  background: #f8f8f8;
  border-color: #2196f3;
}

.ontology-item.active {
  background: #e3f2fd;
  border-color: #2196f3;
}

.ontology-name {
  font-weight: 500;
  color: #333;
  margin-bottom: 0.5rem;
}

.ontology-meta {
  font-size: 0.75rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.ontology-date {
  font-size: 0.75rem;
  color: #999;
}

.ontology-details {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.empty-selection,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #999;
}

.ontology-info {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.ontology-info h3 {
  margin: 0 0 0.5rem 0;
  color: #333;
}

.ontology-info p {
  margin: 0.25rem 0;
  color: #666;
  font-size: 0.875rem;
}

.search-results {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
}

.search-results h4 {
  margin: 0 0 1rem 0;
  color: #333;
}

.search-result-item {
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.entity-type {
  padding: 0.25rem 0.5rem;
  background: #e3f2fd;
  color: #2196f3;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.entity-name {
  font-weight: 500;
  color: #333;
}

.result-score {
  margin-left: auto;
  font-size: 0.75rem;
  color: #999;
}

.result-description {
  color: #666;
  font-size: 0.875rem;
  margin: 0.5rem 0;
}

.result-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: #999;
}

.section-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tab {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  color: #666;
  transition: all 0.2s;
}

.tab:hover {
  border-color: #2196f3;
  color: #2196f3;
}

.tab.active {
  background: #2196f3;
  color: white;
  border-color: #2196f3;
}

.tab-content {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
}

.entities-list,
.relationships-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.entity-card,
.relationship-card {
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  transition: all 0.2s;
}

.entity-card:hover,
.relationship-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.entity-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.entity-type-badge {
  padding: 0.25rem 0.5rem;
  background: #e8f5e9;
  color: #4caf50;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.entity-card h4 {
  margin: 0;
  color: #333;
  font-size: 1rem;
}

.entity-description,
.relationship-description {
  color: #666;
  font-size: 0.875rem;
  margin: 0.5rem 0;
}

.entity-source {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: #999;
  margin-top: 0.5rem;
}

.relationship-flow {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.entity-node {
  padding: 0.25rem 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #333;
}

.relationship-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
}

.relationship-type {
  font-size: 0.75rem;
  color: #666;
  margin-bottom: 0.25rem;
}

.relationship-meta {
  font-size: 0.75rem;
  color: #999;
  margin-bottom: 0.5rem;
}

.graph-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 600px;
}

.graph-controls {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  background: #f8f8f8;
  border-radius: 8px;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.control-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #666;
  white-space: nowrap;
}

.control-group select {
  padding: 0.25rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.875rem;
}

.control-group input[type='range'] {
  width: 100px;
}

.control-group input[type='checkbox'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.control-group span {
  font-size: 0.875rem;
  color: #666;
  min-width: 30px;
}

.graph-chart {
  flex: 1;
  min-height: 500px;
  width: 100%;
}
</style>
