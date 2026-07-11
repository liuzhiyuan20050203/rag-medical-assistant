<template>
  <div class="knowledge-page">
    <!-- Header -->
    <header class="page-title ui-page-heading">
      <span class="page-kicker">MEDICAL KNOWLEDGE BASE</span>
      <div class="heading-row">
        <div>
          <h2>知识库</h2>
          <p>
            检索常见疾病、常用药品与危险警示规则。AI 咨询会依据这里的内容组织更可靠、更安全的参考建议。
          </p>
        </div>
        <button type="button" class="refresh-btn ui-button ui-button--soft" @click="loadKnowledge(true)" :disabled="loading">
          <RefreshCw :class="{ spin: loading }" :size="16" aria-hidden="true" />
          {{ loading ? '正在同步...' : '同步数据' }}
        </button>
      </div>
    </header>

    <!-- Search & Filter Tab Area -->
    <div class="filter-toolbar">
      <div class="search-input-box">
        <Search :size="18" class="search-icon" aria-hidden="true" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索疾病、症状、药品用途或成份..."
          aria-label="检索知识库"
        />
        <button v-if="searchQuery" type="button" class="clear-search-btn" @click="searchQuery = ''">
          <X :size="16" aria-hidden="true" />
        </button>
      </div>

      <div class="tabs ui-tabs">
        <button
          class="ui-tab"
          :class="{ active: activeTab === 'all' }"
          @click="activeTab = 'all'"
        >
          全部知识
        </button>
        <button
          class="ui-tab"
          :class="{ active: activeTab === 'disease' }"
          @click="activeTab = 'disease'"
        >
          常见疾病
        </button>
        <button
          class="ui-tab"
          :class="{ active: activeTab === 'medicine' }"
          @click="activeTab = 'medicine'"
        >
          常用药品
        </button>
        <button
          class="ui-tab"
          :class="{ active: activeTab === 'warning' }"
          @click="activeTab = 'warning'"
        >
          危险警示词
        </button>
      </div>
    </div>

    <!-- Loading empty states -->
    <div v-if="loading" class="loading ui-empty">
      正在加载知识库数据，请稍候...
    </div>

    <section v-if="!loading" class="content-section">
      <div class="section-header">
        <div>
          <h3>{{ activeLabel }}</h3>
          <span>共 {{ currentTotal }} 条结果，显示第 {{ displayStart }} 至 {{ displayEnd }} 条</span>
        </div>

        <label class="page-size-control">
          每页
          <select v-model.number="pageSize" aria-label="每页显示条数">
            <option v-for="option in pageSizeOptions" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
          条
        </label>
      </div>

      <div v-if="currentTotal === 0" class="ui-empty">
        未找到匹配的知识条目，请换个词重新搜索。
      </div>

      <!-- Card Grid -->
      <div v-else class="knowledge-grid">
        <article
          v-for="(item, index) in pagedItems"
          :key="knowledgeKey(item, index)"
          class="knowledge-card ui-card"
          :class="[`card-type-${item.type}`]"
        >
          <div class="card-head">
            <div class="title-wrap">
              <span class="row-index">{{ startIndex + index + 1 }}</span>
              <h4>{{ item.name }}</h4>
            </div>
            <span :class="['type-badge', `badge-${item.type}`]">{{ item.tag }}</span>
          </div>

          <p class="card-summary">{{ item.summary }}</p>

          <div class="card-footer">
            <button type="button" class="details-link-btn" @click="selectedItem = item">
              <span>查看详情</span>
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
          </div>
        </article>
      </div>

      <!-- Pagination footer -->
      <nav v-if="currentTotal > 0" class="pagination-bar" aria-label="知识库分页">
        <span>第 {{ currentPage }} / {{ totalPages }} 页</span>

        <div class="pager-buttons">
          <button
            type="button"
            title="第一页"
            aria-label="第一页"
            :disabled="currentPage === 1"
            @click="currentPage = 1"
          >
            <ChevronsLeft :size="18" aria-hidden="true" />
          </button>
          <button
            type="button"
            title="上一页"
            aria-label="上一页"
            :disabled="currentPage === 1"
            @click="currentPage = currentPage - 1"
          >
            <ChevronLeft :size="18" aria-hidden="true" />
          </button>

          <button
            v-for="page in visiblePageNumbers"
            :key="page"
            type="button"
            class="page-number"
            :class="{ active: page === currentPage }"
            :aria-label="`第 ${page} 页`"
            @click="currentPage = page"
          >
            {{ page }}
          </button>

          <button
            type="button"
            title="下一页"
            aria-label="下一页"
            :disabled="currentPage === totalPages"
            @click="currentPage = currentPage + 1"
          >
            <ChevronRight :size="18" aria-hidden="true" />
          </button>
          <button
            type="button"
            title="最后一页"
            aria-label="最后一页"
            :disabled="currentPage === totalPages"
            @click="currentPage = totalPages"
          >
            <ChevronsRight :size="18" aria-hidden="true" />
          </button>
        </div>
      </nav>
    </section>

    <!-- Detail Sliding Drawer overlay -->
    <Transition name="slide-fade">
      <div v-if="selectedItem" class="drawer-overlay" @click="selectedItem = null">
        <div class="drawer-content" @click.stop>
          <header class="drawer-header">
            <div class="drawer-title-wrap">
              <span :class="['type-badge', `badge-${selectedItem.type}`]">
                {{ selectedItem.type === 'disease' ? '常见疾病' : selectedItem.type === 'medicine' ? '常用药品' : '危险警示词' }}
              </span>
              <h3>{{ selectedItem.name }}</h3>
            </div>
            <button type="button" class="close-drawer-btn" title="关闭详情" @click="selectedItem = null">
              <X :size="20" aria-hidden="true" />
            </button>
          </header>

          <div class="drawer-body">
            <!-- Disease Detail Layout -->
            <template v-if="selectedItem.type === 'disease'">
              <div class="detail-group">
                <label>疾病常识描述</label>
                <p>{{ fieldText(selectedItem.raw.description) }}</p>
              </div>
              <div class="detail-group">
                <label>常见症状特征</label>
                <p class="highlight-text">{{ fieldText(selectedItem.raw.symptoms) }}</p>
              </div>
              <div class="detail-group">
                <label>日常护理方案</label>
                <p>{{ fieldText(selectedItem.raw.care_advice) }}</p>
              </div>
              <div class="detail-group">
                <label>用药注意细节</label>
                <p>{{ fieldText(selectedItem.raw.medicine_notice) }}</p>
              </div>
              <div class="detail-group danger-notice">
                <label>⚠️ 安全就医提醒</label>
                <p>{{ fieldText(selectedItem.raw.warning) }}</p>
              </div>
            </template>

            <!-- Medicine Detail Layout -->
            <template v-else-if="selectedItem.type === 'medicine'">
              <div class="detail-group">
                <label>药品分类</label>
                <p>{{ fieldText(selectedItem.raw.type) }}</p>
              </div>
              <div class="detail-group">
                <label>临床主要用途</label>
                <p class="highlight-text">{{ fieldText(selectedItem.raw.usage) }}</p>
              </div>
              <div class="detail-group">
                <label>服用禁忌人群</label>
                <p class="warning-text">{{ fieldText(selectedItem.raw.contraindication) }}</p>
              </div>
              <div class="detail-group">
                <label>可能发生的不良反应</label>
                <p>{{ fieldText(selectedItem.raw.side_effect) }}</p>
              </div>
              <div class="detail-group">
                <label>日常使用注意事项</label>
                <p>{{ fieldText(selectedItem.raw.notice) }}</p>
              </div>
            </template>

            <!-- Warning Detail Layout -->
            <template v-else>
              <div class="detail-group danger-notice">
                <label>⚠️ 危险分诊判定规则</label>
                <p>
                  该词条被系统定义为「危险症状规则」核心监测词。当用户描述的病情症状中包含此名词（如胸痛、呼吸困难等紧急病征）时，AI 会首先匹配就医分诊哨兵逻辑，直接输出就医警示，保障高危病情能引起用户的足够重视并及时就医。
                </p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  RefreshCw,
  Search,
  X,
} from '@lucide/vue'
import { cachedGetJson } from '../api'

const loading = ref(false)
const searchQuery = ref('')
const activeTab = ref('all')
const selectedItem = ref(null)

const diseases = ref([])
const medicines = ref([])
const warningRules = ref([])

const currentPage = ref(1)
const pageSize = ref(8)
const pageSizeOptions = [6, 8, 12, 16, 24]

const tabLabels = {
  all: '全部知识',
  disease: '常见疾病常识库',
  medicine: '常用药品说明库',
  warning: '高危分诊规则库',
}

const activeLabel = computed(() => tabLabels[activeTab.value])

// Build unified items
const unifiedItems = computed(() => {
  const result = []

  // Diseases mapping
  diseases.value.forEach(item => {
    result.push({
      type: 'disease',
      name: item.name,
      tag: item.category || '常见病',
      summary: item.description || '暂无疾病描述信息。',
      raw: item
    })
  })

  // Medicines mapping
  medicines.value.forEach(item => {
    result.push({
      type: 'medicine',
      name: item.name,
      tag: item.type || '非处方药',
      summary: item.usage || '暂无说明用途。',
      raw: item
    })
  })

  // Warning rules mapping
  warningRules.value.forEach(item => {
    result.push({
      type: 'warning',
      name: item,
      tag: '高危警示',
      summary: `危险症状筛查规则：当描述病情触发包含“${item}”在内的敏感词时，将触发分诊策略。`,
      raw: item
    })
  })

  return result
})

// Dynamic search & category filter
const filteredItems = computed(() => {
  let list = unifiedItems.value

  if (activeTab.value !== 'all') {
    list = list.filter(item => item.type === activeTab.value)
  }

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    list = list.filter(item =>
      item.name.toLowerCase().includes(query) ||
      item.summary.toLowerCase().includes(query) ||
      item.tag.toLowerCase().includes(query)
    )
  }

  return list
})

// Pagination
const currentTotal = computed(() => filteredItems.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(currentTotal.value / pageSize.value)))
const startIndex = computed(() => (currentPage.value - 1) * pageSize.value)
const displayStart = computed(() => (currentTotal.value > 0 ? startIndex.value + 1 : 0))
const displayEnd = computed(() => Math.min(currentTotal.value, startIndex.value + pageSize.value))
const pagedItems = computed(() => filteredItems.value.slice(startIndex.value, startIndex.value + pageSize.value))

const visiblePageNumbers = computed(() => {
  const maxVisible = 5
  let firstPage = Math.max(1, currentPage.value - 2)
  let lastPage = Math.min(totalPages.value, firstPage + maxVisible - 1)

  firstPage = Math.max(1, lastPage - maxVisible + 1)

  return Array.from({ length: lastPage - firstPage + 1 }, (_, index) => firstPage + index)
})

const fieldText = (value) => {
  if (Array.isArray(value)) {
    return value.filter(Boolean).join('、') || '暂无'
  }

  return String(value || '').trim() || '暂无'
}

const knowledgeKey = (item, index) => {
  const absoluteIndex = startIndex.value + index
  return `${item.type}-${item.name}-${absoluteIndex}`
}

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
    console.error(error)
  } finally {
    loading.value = false
  }
}

watch([activeTab, searchQuery, pageSize], () => {
  currentPage.value = 1
})

onMounted(() => {
  loadKnowledge()
})
</script>

<style scoped>
.knowledge-page {
  display: grid;
  gap: 24px;
}

.page-title {
  position: relative;
  margin-bottom: 0;
  padding: 26px 28px;
  overflow: hidden;
  background:
    radial-gradient(circle at 92% 12%, rgba(13, 148, 136, 0.13), transparent 30%),
    linear-gradient(135deg, rgba(239, 246, 255, 0.95), rgba(255, 255, 255, 0.96) 55%, rgba(240, 253, 250, 0.82));
  border: 1px solid #dce7f2;
  border-radius: 22px;
  box-shadow: 0 18px 45px rgba(27, 57, 91, 0.07);
}

.page-kicker {
  color: var(--teal);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.15em;
}

.heading-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.heading-row p {
  margin-top: 8px;
}

.refresh-btn {
  flex: 0 0 auto;
  width: fit-content;
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
}

/* Search bar styling */
.filter-toolbar {
  display: grid;
  grid-template-columns: minmax(280px, 440px) 1fr;
  align-items: center;
  gap: 20px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(14px);
}

.search-input-box {
  position: relative;
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0 12px;
  min-height: 40px;
  box-shadow: none;
}

.search-input-box:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.search-icon {
  color: var(--text-muted);
  margin-right: 8px;
}

.search-input-box input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14.5px;
  color: var(--text-primary);
  background: transparent;
}

.clear-search-btn {
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
}

.clear-search-btn:hover {
  color: var(--danger);
}

.filter-toolbar .tabs {
  justify-content: flex-end;
  margin-bottom: 0;
}

.filter-toolbar .ui-tab {
  min-height: 38px;
  padding: 0 13px;
  font-size: 13px;
}

.content-section {
  display: grid;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-header h3 {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.section-header span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
}

.page-size-control {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.page-size-control select {
  min-height: 36px;
  padding: 0 28px 0 10px;
  color: var(--text-secondary);
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 9px;
  outline: 0;
  font-weight: 800;
}

/* Category list styling */
.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.knowledge-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 20px;
  min-height: 160px;
  overflow: hidden;
  background: linear-gradient(145deg, #ffffff, #fbfdff);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.knowledge-card::before {
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  content: '';
  background: var(--primary);
  opacity: 0.8;
}

.knowledge-card.card-type-medicine::before {
  background: var(--teal);
}

.knowledge-card.card-type-warning::before {
  background: var(--danger);
}

.knowledge-card:hover {
  transform: translateY(-2px);
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.row-index {
  display: inline-grid;
  width: 26px;
  height: 26px;
  place-items: center;
  font-size: 11.5px;
  font-weight: 800;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: var(--radius-xs);
  flex: 0 0 auto;
}

.title-wrap h4 {
  font-size: 16.5px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type-badge {
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 800;
  border-radius: 999px;
  white-space: nowrap;
}

.badge-disease {
  background: var(--primary-soft);
  color: var(--primary);
  border: 1px solid #bfdbfe;
}

.badge-medicine {
  background: var(--teal-soft);
  color: var(--teal);
  border: 1px solid #99f6e4;
}

.badge-warning {
  background: var(--danger-soft);
  color: var(--danger);
  border: 1px solid var(--danger-border);
}

.card-summary {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin: 0 0 16px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
}

.details-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  color: var(--primary);
  font-size: 13.5px;
  font-weight: 800;
  cursor: pointer;
  transition: color 0.2s;
  padding: 4px;
  border-radius: 4px;
}

.details-link-btn:hover {
  color: var(--primary-hover);
}

/* Pagination */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  margin-top: 10px;
}

.pagination-bar > span {
  font-size: 14px;
  color: var(--text-muted);
  font-weight: 700;
}

.pager-buttons {
  display: flex;
  gap: 6px;
}

.pager-buttons button {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.pager-buttons button:hover:not(:disabled),
.pager-buttons button.active {
  color: #ffffff;
  background: var(--primary);
  border-color: var(--primary);
}

.pager-buttons button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-number {
  font-size: 13.5px;
  font-weight: 700;
}

/* Drawer Detail Panel (Apple-health overlay style) */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.3);
  z-index: 1000;
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
}

.drawer-content {
  width: min(100%, 480px);
  height: 100%;
  background: #ffffff;
  box-shadow: -10px 0 30px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-direction: column;
  padding: 28px;
  animation: slideIn 0.3s ease-out;
}

.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 18px;
  margin-bottom: 20px;
}

.drawer-title-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.drawer-title-wrap h3 {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
}

.close-drawer-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--surface-soft);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.close-drawer-btn:hover {
  background: var(--danger-soft);
  color: var(--danger);
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.detail-group {
  margin-bottom: 20px;
}

.detail-group label {
  display: block;
  font-size: 13px;
  font-weight: 800;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.detail-group p {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-primary);
  margin: 0;
}

.highlight-text {
  font-weight: 600;
  color: var(--primary) !important;
}

.warning-text {
  font-weight: 600;
  color: var(--danger) !important;
}

.danger-notice {
  background: var(--danger-soft);
  border: 1px solid var(--danger-border);
  padding: 14px;
  border-radius: 12px;
  color: #7f1d1d;
}

.danger-notice label {
  color: var(--danger);
}

/* Animations */
@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.26s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
}

.slide-fade-enter-from .drawer-content,
.slide-fade-leave-to .drawer-content {
  transform: translateX(100%);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 900px) {
  .filter-toolbar {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .search-input-box {
    max-width: 100%;
  }

  .filter-toolbar .tabs {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .page-title {
    padding: 22px;
  }

  .heading-row,
  .section-header {
    align-items: stretch;
    flex-direction: column;
  }

  .knowledge-grid {
    grid-template-columns: 1fr;
  }
  .pagination-bar {
    flex-direction: column;
    gap: 14px;
    align-items: center;
  }
}
</style>
