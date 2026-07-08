<template>
  <div class="page">
    <div class="page-title">
      <h2>系统知识库</h2>
      <p>
        本页面展示系统当前内置的常见病知识库、药品知识库和危险症状规则库。
        AI 医疗助手会基于这些知识内容进行检索和回答。
      </p>
      <button type="button" class="refresh-btn" @click="loadKnowledge(true)" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新数据' }}
      </button>
    </div>

    <div class="tabs">
      <button
        :class="{ active: activeTab === 'disease' }"
        @click="activeTab = 'disease'"
      >
        常见病知识库
      </button>

      <button
        :class="{ active: activeTab === 'medicine' }"
        @click="activeTab = 'medicine'"
      >
        药品知识库
      </button>

      <button
        :class="{ active: activeTab === 'warning' }"
        @click="activeTab = 'warning'"
      >
        危险症状规则库
      </button>
    </div>

    <div v-if="loading" class="loading">
      数据加载中...
    </div>

    <section v-if="activeTab === 'disease' && !loading" class="content-section">
      <div class="section-header">
        <h3>常见病知识库</h3>
        <span>共 {{ diseases.length }} 条</span>
      </div>

      <div class="card-list">
        <div
          v-for="(item, index) in diseases"
          :key="index"
          class="knowledge-card"
        >
          <div class="card-title">
            <h4>{{ item.name }}</h4>
            <span>{{ item.category }}</span>
          </div>

          <p><strong>常见症状：</strong>{{ item.symptoms.join('、') }}</p>
          <p><strong>疾病描述：</strong>{{ item.description }}</p>
          <p><strong>护理建议：</strong>{{ item.care_advice }}</p>
          <p><strong>用药注意：</strong>{{ item.medicine_notice }}</p>
          <p><strong>就医提醒：</strong>{{ item.warning }}</p>
        </div>
      </div>
    </section>

    <section v-if="activeTab === 'medicine' && !loading" class="content-section">
      <div class="section-header">
        <h3>药品知识库</h3>
        <span>共 {{ medicines.length }} 条</span>
      </div>

      <div class="card-list">
        <div
          v-for="(item, index) in medicines"
          :key="index"
          class="knowledge-card"
        >
          <div class="card-title">
            <h4>{{ item.name }}</h4>
            <span>{{ item.type }}</span>
          </div>

          <p><strong>适用情况：</strong>{{ item.usage }}</p>
          <p><strong>注意事项：</strong>{{ item.notice }}</p>
          <p><strong>禁忌人群：</strong>{{ item.contraindication }}</p>
          <p><strong>不良反应：</strong>{{ item.side_effect }}</p>
        </div>
      </div>
    </section>

    <section v-if="activeTab === 'warning' && !loading" class="content-section">
      <div class="section-header">
        <h3>危险症状规则库</h3>
        <span>共 {{ warningRules.length }} 条</span>
      </div>

      <div class="warning-grid">
        <div
          v-for="(item, index) in warningRules"
          :key="index"
          class="warning-item"
        >
          {{ item }}
        </div>
      </div>

      <div class="notice">
        当用户输入内容中包含以上危险症状关键词时，系统会优先返回就医提醒，
        不再进行普通健康咨询回答。
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { cachedGetJson } from '../api'

const activeTab = ref('disease')
const loading = ref(false)

const diseases = ref([])
const medicines = ref([])
const warningRules = ref([])

const loadKnowledge = async (force = false) => {
  loading.value = true

  try {
    const [diseaseData, medicineData, warningData] = await Promise.all([
      cachedGetJson('knowledge:diseases', '/api/disease/list', { force }),
      cachedGetJson('knowledge:medicines', '/api/medicine/list', { force }),
      cachedGetJson('knowledge:warnings', '/api/warning/list', { force }),
    ])

    diseases.value = diseaseData.data || []
    medicines.value = medicineData.data || []
    warningRules.value = warningData.data || []
  } catch (error) {
    alert('知识库加载失败，请检查后端服务是否正常运行。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadKnowledge()
})
</script>

<style scoped>
.page-title {
  margin-bottom: 24px;
}

.refresh-btn {
  margin-top: 14px;
  min-height: 38px;
  padding: 0 14px;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 800;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.page-title h2 {
  font-size: 30px;
  margin-bottom: 10px;
  color: #111827;
}

.page-title p {
  color: #6b7280;
  line-height: 1.8;
}

.tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.tabs button {
  padding: 11px 20px;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 999px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
}

.tabs button.active {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
}

.loading {
  background: white;
  padding: 26px;
  border-radius: 16px;
  color: #6b7280;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.content-section {
  margin-top: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.section-header h3 {
  font-size: 22px;
  color: #111827;
}

.section-header span {
  color: #2563eb;
  font-weight: 700;
}

.card-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
}

.knowledge-card {
  background: white;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.card-title h4 {
  color: #111827;
  font-size: 20px;
}

.card-title span {
  background: #eff6ff;
  color: #2563eb;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
}

.knowledge-card p {
  color: #374151;
  line-height: 1.8;
  margin-bottom: 8px;
}

.warning-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.warning-item {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
  padding: 10px 16px;
  border-radius: 999px;
  font-weight: 600;
}

.notice {
  margin-top: 24px;
  background: #fff7ed;
  color: #9a3412;
  padding: 18px 22px;
  border-radius: 12px;
  border: 1px solid #fed7aa;
  line-height: 1.8;
}
</style>
