<template>
  <div class="page">
    <div class="page-title ui-page-heading">
      <h2>系统知识库</h2>
      <p>
        本页面展示系统当前内置的常见病知识库和药品知识库。
        AI 医疗助手会基于这些知识内容进行检索和回答。
      </p>
      <button type="button" class="refresh-btn ui-button ui-button--soft" @click="loadKnowledge(true)" :disabled="loading">
        <RefreshCw :class="{ spin: loading }" :size="16" aria-hidden="true" />
        {{ loading ? '刷新中...' : '刷新数据' }}
      </button>
    </div>

    <section class="knowledge-search ui-card" aria-label="知识库搜索">
      <div>
        <strong>搜索知识库</strong>
        <span>按当前分类筛选名称、症状、用途、注意事项等内容。</span>
      </div>

      <label>
        <Search :size="18" aria-hidden="true" />
        <input
          v-model.trim="searchKeyword"
          type="search"
          :placeholder="searchPlaceholder"
          aria-label="搜索知识库"
        />
        <button
          v-if="searchKeyword"
          type="button"
          title="清空搜索"
          aria-label="清空搜索"
          @click="clearSearch"
        >
          ×
        </button>
      </label>
    </section>

    <div class="tabs ui-tabs">
      <button
        class="ui-tab"
        :class="{ active: activeTab === 'disease' }"
        @click="setTab('disease')"
      >
        常见病知识库
      </button>

      <button
        class="ui-tab"
        :class="{ active: activeTab === 'medicine' }"
        @click="setTab('medicine')"
      >
        药品知识库
      </button>

      <button
        v-if="isAdmin"
        class="ui-tab"
        :class="{ active: activeTab === 'warning' }"
        @click="setTab('warning')"
      >
        危险症状规则库
      </button>
    </div>

    <div v-if="loading" class="loading ui-empty">
      数据加载中...
    </div>

    <section v-if="!loading" class="content-section">
      <div class="section-header">
        <div>
          <h3>{{ activeLabel }}</h3>
          <span>
            共 {{ currentTotal }} 条，当前显示 {{ displayStart }}-{{ displayEnd }} 条
            <template v-if="searchKeyword">，已按“{{ searchKeyword }}”筛选</template>
          </span>
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
        {{ searchKeyword ? '没有匹配的知识库内容，请换个关键词试试。' : '暂无知识库内容。' }}
      </div>

      <div v-else class="knowledge-list">
        <article
          v-for="(item, index) in pagedItems"
          :key="knowledgeKey(item, index)"
          class="knowledge-row ui-card"
          :class="{ 'knowledge-row--warning': activeTab === 'warning' }"
        >
          <template v-if="activeTab === 'disease'">
            <div class="row-head">
              <div class="title-wrap">
                <span class="row-index">{{ startIndex + index + 1 }}</span>
                <h4>{{ item.name }}</h4>
              </div>
              <span class="ui-badge ui-badge--info">{{ fieldText(item.category) }}</span>
            </div>

            <p class="row-summary">{{ fieldText(item.description) }}</p>

            <dl class="knowledge-fields">
              <div>
                <dt>常见症状</dt>
                <dd>{{ fieldText(item.symptoms) }}</dd>
              </div>
              <div>
                <dt>护理建议</dt>
                <dd>{{ fieldText(item.care_advice) }}</dd>
              </div>
              <div>
                <dt>用药注意</dt>
                <dd>{{ fieldText(item.medicine_notice) }}</dd>
              </div>
              <div>
                <dt>就医提醒</dt>
                <dd>{{ fieldText(item.warning) }}</dd>
              </div>
            </dl>
          </template>

          <template v-else-if="activeTab === 'medicine'">
            <div class="row-head">
              <div class="title-wrap">
                <span class="row-index">{{ startIndex + index + 1 }}</span>
                <h4>{{ item.name }}</h4>
              </div>
              <span class="ui-badge ui-badge--info">{{ fieldText(item.type) }}</span>
            </div>

            <dl class="knowledge-fields">
              <div>
                <dt>适用情况</dt>
                <dd>{{ fieldText(item.usage) }}</dd>
              </div>
              <div>
                <dt>注意事项</dt>
                <dd>{{ fieldText(item.notice) }}</dd>
              </div>
              <div>
                <dt>禁忌人群</dt>
                <dd>{{ fieldText(item.contraindication) }}</dd>
              </div>
              <div>
                <dt>不良反应</dt>
                <dd>{{ fieldText(item.side_effect) }}</dd>
              </div>
            </dl>
          </template>

          <template v-else>
            <div class="row-head">
              <div class="title-wrap">
                <span class="row-index">{{ startIndex + index + 1 }}</span>
                <h4>{{ item }}</h4>
              </div>
              <span class="ui-badge ui-badge--danger">危险规则</span>
            </div>

            <p class="row-summary">命中后优先返回就医提醒。</p>
          </template>
        </article>
      </div>

      <nav v-if="currentTotal > 0" class="pagination-bar" aria-label="知识库分页">
        <span>第 {{ currentPage }} / {{ totalPages }} 页</span>

        <div class="pager-buttons">
          <button
            type="button"
            title="第一页"
            aria-label="第一页"
            :disabled="currentPage === 1"
            @click="setPage(1)"
          >
            <ChevronsLeft :size="18" aria-hidden="true" />
          </button>
          <button
            type="button"
            title="上一页"
            aria-label="上一页"
            :disabled="currentPage === 1"
            @click="setPage(currentPage - 1)"
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
            @click="setPage(page)"
          >
            {{ page }}
          </button>

          <button
            type="button"
            title="下一页"
            aria-label="下一页"
            :disabled="currentPage === totalPages"
            @click="setPage(currentPage + 1)"
          >
            <ChevronRight :size="18" aria-hidden="true" />
          </button>
          <button
            type="button"
            title="最后一页"
            aria-label="最后一页"
            :disabled="currentPage === totalPages"
            @click="setPage(totalPages)"
          >
            <ChevronsRight :size="18" aria-hidden="true" />
          </button>
        </div>
      </nav>

      <div v-if="activeTab === 'warning'" class="notice ui-alert ui-alert--warning">
        当用户输入内容中包含以上危险症状关键词时，系统会优先返回就医提醒，
        不再进行普通健康咨询回答。
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  RefreshCw,
  Search,
} from '@lucide/vue'
import { cachedGetJson } from '../api'

const activeTab = ref('disease')
const loading = ref(false)
const searchKeyword = ref('')
const currentUser = ref(null)

const diseases = ref([])
const medicines = ref([])
const warningRules = ref([])
const currentPageByTab = reactive({
  disease: 1,
  medicine: 1,
  warning: 1,
})
const pageSizeByTab = reactive({
  disease: 8,
  medicine: 8,
  warning: 16,
})

const tabLabels = {
  disease: '常见病知识库',
  medicine: '药品知识库',
  warning: '危险症状规则库',
}
const pageSizeOptions = [6, 8, 12, 16, 24]

const loadCurrentUser = () => {
  try {
    const raw = localStorage.getItem('ragUser')
    currentUser.value = raw ? JSON.parse(raw) : null
  } catch (error) {
    console.error(error)
    currentUser.value = null
  }
}

const isAdmin = computed(() => currentUser.value?.role === 'admin')
const activeLabel = computed(() => tabLabels[activeTab.value])
const searchPlaceholder = computed(() => {
  if (activeTab.value === 'medicine') return '搜索药品名称、类别、适用情况...'
  if (activeTab.value === 'warning') return '搜索危险症状关键词...'
  return '搜索疾病名称、症状、护理建议...'
})
const rawCurrentItems = computed(() => {
  if (activeTab.value === 'medicine') {
    return medicines.value
  }

  if (activeTab.value === 'warning') {
    return isAdmin.value ? warningRules.value : []
  }

  return diseases.value
})
const currentItems = computed(() => {
  const keyword = normalizeSearchText(searchKeyword.value)
  if (!keyword) return rawCurrentItems.value

  return rawCurrentItems.value.filter((item) => {
    return searchableText(item).includes(keyword)
  })
})
const currentTotal = computed(() => currentItems.value.length)
const pageSize = computed({
  get: () => pageSizeByTab[activeTab.value],
  set: (value) => {
    pageSizeByTab[activeTab.value] = Number(value) || 8
    currentPageByTab[activeTab.value] = 1
  },
})
const totalPages = computed(() => Math.max(1, Math.ceil(currentTotal.value / pageSize.value)))
const currentPage = computed({
  get: () => Math.min(currentPageByTab[activeTab.value], totalPages.value),
  set: (value) => {
    const nextPage = Number(value) || 1
    currentPageByTab[activeTab.value] = Math.min(Math.max(nextPage, 1), totalPages.value)
  },
})
const startIndex = computed(() => (currentPage.value - 1) * pageSize.value)
const displayStart = computed(() => (currentTotal.value > 0 ? startIndex.value + 1 : 0))
const displayEnd = computed(() => Math.min(currentTotal.value, startIndex.value + pageSize.value))
const pagedItems = computed(() => currentItems.value.slice(startIndex.value, startIndex.value + pageSize.value))
const visiblePageNumbers = computed(() => {
  const maxVisible = 5
  let firstPage = Math.max(1, currentPage.value - 2)
  let lastPage = Math.min(totalPages.value, firstPage + maxVisible - 1)

  firstPage = Math.max(1, lastPage - maxVisible + 1)

  return Array.from({ length: lastPage - firstPage + 1 }, (_, index) => firstPage + index)
})

const setTab = (tab) => {
  if (tab === 'warning' && !isAdmin.value) {
    activeTab.value = 'disease'
    return
  }

  activeTab.value = tab
  currentPageByTab[tab] = 1
}

const setPage = (page) => {
  currentPage.value = page
}

const fieldText = (value) => {
  if (Array.isArray(value)) {
    return value.filter(Boolean).join('、') || '暂无'
  }

  return String(value || '').trim() || '暂无'
}

const normalizeSearchText = (value) => {
  return String(value || '').replace(/\s+/g, '').toLowerCase()
}

const searchableText = (item) => {
  if (activeTab.value === 'warning') {
    return normalizeSearchText(item)
  }

  if (!item || typeof item !== 'object') {
    return ''
  }

  return normalizeSearchText([
    item.name,
    item.category,
    item.description,
    item.symptoms,
    item.care_advice,
    item.medicine_notice,
    item.warning,
    item.type,
    item.usage,
    item.notice,
    item.contraindication,
    item.side_effect,
  ].map(fieldText).join(' '))
}

const clearSearch = () => {
  searchKeyword.value = ''
}

const knowledgeKey = (item, index) => {
  const absoluteIndex = startIndex.value + index

  if (activeTab.value === 'warning') {
    return `warning-${item}-${absoluteIndex}`
  }

  return item.id || `${activeTab.value}-${item.name}-${absoluteIndex}`
}

const clampCurrentPage = () => {
  currentPageByTab[activeTab.value] = Math.min(
    Math.max(currentPageByTab[activeTab.value], 1),
    totalPages.value,
  )
}

const loadKnowledge = async (force = false) => {
  loading.value = true

  try {
    const requests = [
      cachedGetJson('knowledge:diseases', '/api/disease/list', { force }),
      cachedGetJson('knowledge:medicines', '/api/medicine/list', { force }),
    ]

    if (isAdmin.value) {
      requests.push(cachedGetJson('knowledge:warnings', '/api/warning/list', { force }))
    }

    const [diseaseData, medicineData, warningData] = await Promise.all(requests)

    diseases.value = diseaseData.data || []
    medicines.value = medicineData.data || []
    warningRules.value = isAdmin.value ? (warningData?.data || []) : []
    clampCurrentPage()
  } catch (error) {
    alert('知识库加载失败，请检查后端服务是否正常运行。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

watch([activeTab, currentTotal, pageSize, searchKeyword], () => {
  clampCurrentPage()
})

watch(isAdmin, (nextIsAdmin) => {
  if (!nextIsAdmin && activeTab.value === 'warning') {
    activeTab.value = 'disease'
  }
  loadKnowledge(true)
})

onMounted(() => {
  loadCurrentUser()
  loadKnowledge()
  window.addEventListener('storage', loadCurrentUser)
  window.addEventListener('rag-user-change', loadCurrentUser)
})

onBeforeUnmount(() => {
  window.removeEventListener('storage', loadCurrentUser)
  window.removeEventListener('rag-user-change', loadCurrentUser)
})
</script>

<style scoped>
.page-title {
  margin-bottom: 18px;
}

.refresh-btn {
  gap: 7px;
  margin-top: 14px;
  min-height: 38px;
  padding: 0 14px;
  width: fit-content;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.knowledge-search {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(280px, 1.2fr);
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
  padding: 14px 16px;
}

.knowledge-search strong,
.knowledge-search span {
  display: block;
}

.knowledge-search strong {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 900;
}

.knowledge-search span {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.knowledge-search label {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 32px;
  gap: 8px;
  align-items: center;
  min-height: 44px;
  padding: 0 10px;
  color: var(--text-muted);
  background: #f8fbfd;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.knowledge-search label:focus-within {
  color: var(--medical-blue);
  background: #ffffff;
  border-color: var(--medical-blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.knowledge-search input {
  width: 100%;
  min-height: 42px;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  outline: none;
}

.knowledge-search button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border-radius: 999px;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}

.knowledge-search button:hover {
  color: #991b1b;
  background: #fee2e2;
}

.content-section {
  display: grid;
  gap: 14px;
  margin-top: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  padding-bottom: 6px;
}

.section-header h3 {
  font-size: 22px;
  color: var(--text-primary);
}

.section-header span {
  display: block;
  margin-top: 4px;
  color: var(--medical-blue);
  font-weight: 700;
}

.page-size-control {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-weight: 800;
}

.page-size-control select {
  min-width: 76px;
  min-height: 38px;
  padding: 0 10px;
  color: var(--text-primary);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  outline: none;
  font-weight: 800;
}

.page-size-control select:focus {
  border-color: var(--medical-blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.knowledge-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.knowledge-row {
  display: grid;
  gap: 10px;
  padding: 15px;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.knowledge-row:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.knowledge-row--warning {
  border-color: var(--danger-border);
  background: linear-gradient(90deg, var(--danger-soft), var(--surface) 46%);
}

.row-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.title-wrap {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.row-index {
  display: inline-grid;
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  place-items: center;
  color: var(--medical-blue);
  background: var(--info-soft);
  border: 1px solid var(--info-border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 900;
}

.title-wrap h4 {
  min-width: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.row-summary {
  color: var(--text-secondary);
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.knowledge-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.knowledge-fields div {
  min-width: 0;
  padding: 10px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: var(--radius-sm);
}

.knowledge-fields dt {
  color: var(--medical-blue);
  font-size: 13px;
  font-weight: 900;
}

.knowledge-fields dd {
  margin-top: 5px;
  color: var(--text-secondary);
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.pagination-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.pagination-bar > span {
  color: var(--text-muted);
  font-weight: 800;
}

.pager-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pager-buttons button {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 900;
}

.pager-buttons button:hover:not(:disabled),
.pager-buttons button.active {
  color: #ffffff;
  background: var(--medical-blue);
  border-color: var(--medical-blue);
}

.pager-buttons button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-number {
  font-size: 14px;
}

.notice {
  margin-top: 4px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 700px) {
  .knowledge-search {
    grid-template-columns: 1fr;
  }

  .section-header,
  .row-head,
  .pagination-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .page-size-control {
    justify-content: space-between;
    width: 100%;
  }

  .knowledge-fields {
    grid-template-columns: 1fr;
  }

  .pager-buttons {
    justify-content: center;
  }
}
</style>
