<!-- 开发者设置 -->
<template>
  <div class="developer-settings">
    <h3>🛠️ 开发者选项</h3>

    <div class="setting-item">
      <label class="setting-label">
        <input
          type="checkbox"
          v-model="showCostAnalysis"
          @change="handleToggleCostAnalysis"
        />
        <span>显示真实成本分析</span>
      </label>
      <p class="setting-description">
        在聊天界面显示详细的 Token 成本分析（Anthropic 定价）
      </p>
    </div>

    <div v-if="showCostAnalysis" class="info-box">
      <p>✅ 成本分析已启用</p>
      <p class="info-text">
        刷新页面后，聊天界面将显示详细的 Token 成本统计卡片，包括：
      </p>
      <ul>
        <li>常规输入 tokens ($3/MTok)</li>
        <li>缓存创建 tokens ($3.75/MTok, 1.25×)</li>
        <li>缓存读取 tokens ($0.30/MTok, 节省90%)</li>
        <li>输出生成 tokens ($15/MTok)</li>
        <li>成本对比和优化建议</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const showCostAnalysis = ref(false)

onMounted(() => {
  // 从 localStorage 读取设置
  showCostAnalysis.value = localStorage.getItem('dev_mode') === 'true'
})

const handleToggleCostAnalysis = () => {
  if (showCostAnalysis.value) {
    localStorage.setItem('dev_mode', 'true')
  } else {
    localStorage.removeItem('dev_mode')
  }

  // 提示需要刷新
  alert('设置已保存，请刷新页面使更改生效')
}
</script>

<style scoped>
.developer-settings {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
}

.developer-settings h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #333;
}

.setting-item {
  margin-bottom: 16px;
}

.setting-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 15px;
  color: #333;
}

.setting-label input[type="checkbox"] {
  margin-right: 8px;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.setting-description {
  margin: 8px 0 0 26px;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

.info-box {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 1px solid #2196f3;
  border-radius: 6px;
  padding: 16px;
  margin-top: 16px;
}

.info-box p {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #1565c0;
}

.info-box p:first-child {
  font-weight: 600;
  font-size: 15px;
}

.info-text {
  margin-top: 12px;
  color: #1976d2 !important;
}

.info-box ul {
  margin: 8px 0 0 20px;
  padding: 0;
  font-size: 13px;
  color: #1976d2;
  line-height: 1.8;
}

.info-box li {
  margin-bottom: 4px;
}
</style>
