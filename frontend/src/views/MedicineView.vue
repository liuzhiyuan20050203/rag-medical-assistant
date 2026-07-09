<template>
  <div class="medicine-page">
    <section class="medicine-hero ui-card" aria-labelledby="medicine-title">
      <div>
        <p class="eyebrow">SMART PHARMACY</p>
        <h2 id="medicine-title">用药查询</h2>
        <p class="desc">
          输入药品名称或药品类别，查询常见用药注意事项、禁忌人群和不良反应。
          系统只提供安全信息参考，不提供处方建议。
        </p>

        <form class="search-box" @submit.prevent="searchMedicine">
          <label class="search-label" for="medicine-keyword">药品名称或类别</label>
          <div class="search-row">
            <input
              id="medicine-keyword"
              class="ui-field"
              v-model="keyword"
              placeholder="例如：布洛芬、解热、抗过敏"
            />

            <button class="ui-button ui-button--primary" type="submit" :disabled="loading">
              {{ loading ? '查询中...' : '查询' }}
            </button>
          </div>
        </form>

        <div class="quick-tags" aria-label="快捷查询">
          <button
            v-for="item in quickKeywords"
            :key="item"
            class="quick-tag ui-button ui-button--soft"
            type="button"
            @click="quickSearch(item)"
          >
            {{ item }}
          </button>
        </div>
      </div>

      <div class="pharmacy-visual" aria-hidden="true">
        <div class="shelf">
          <div class="shelf-header">
            <span>院内药房</span>
            <strong>Rx</strong>
          </div>
          <div class="bottle-row">
            <i></i>
            <i></i>
            <i></i>
            <i></i>
          </div>
          <div class="pill-strip">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </section>

    <section class="safety-panel" aria-label="用药安全核对">
      <article v-for="item in safetyChecklist" :key="item.title" class="ui-card">
        <span>{{ item.code }}</span>
        <strong>{{ item.title }}</strong>
        <p>{{ item.text }}</p>
      </article>
    </section>

    <div v-if="message" class="message ui-alert ui-alert--info">
      {{ message }}
    </div>

    <section v-if="medicines.length > 0" class="medicine-list" aria-label="药品查询结果">
      <article
        v-for="(item, index) in medicines"
        :key="index"
        class="medicine-card ui-card"
      >
        <div class="medicine-card-header">
          <div>
            <span class="medicine-label">药品</span>
            <h3>{{ item.name }}</h3>
          </div>
          <strong class="ui-badge ui-badge--info">{{ item.type }}</strong>
        </div>

        <div class="field-grid">
          <p class="field-item ui-section">
            <strong>适用情况</strong>
            <span>{{ item.usage }}</span>
          </p>
          <p class="field-item ui-section">
            <strong>注意事项</strong>
            <span>{{ item.notice }}</span>
          </p>
          <p class="field-item ui-section">
            <strong>禁忌人群</strong>
            <span>{{ item.contraindication }}</span>
          </p>
          <p class="field-item ui-section">
            <strong>不良反应</strong>
            <span>{{ item.side_effect }}</span>
          </p>
        </div>
      </article>
    </section>

    <section v-else class="empty-state ui-empty">
      <div>
        <strong>药品信息待查询</strong>
        <p>可以从上方快捷标签开始，也可以输入药品名称、药品类别或症状相关关键词。</p>
      </div>
    </section>

    <section class="notice ui-alert ui-alert--warning">
      <strong>提示：</strong>
      用药应严格按照药品说明书或医生、药师指导进行。儿童、孕妇、老人、慢性病患者应谨慎用药。
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { apiUrl } from '../api'

const keyword = ref('')
const medicines = ref([])
const message = ref('')
const loading = ref(false)

const quickKeywords = ['布洛芬', '对乙酰氨基酚', '抗过敏', '止泻', '胃酸']

const safetyChecklist = [
  {
    code: '01',
    title: '核对适用场景',
    text: '先确认药品用于缓解哪类症状，避免把止痛、退热、抗过敏等药物混用。',
  },
  {
    code: '02',
    title: '关注特殊人群',
    text: '儿童、孕妇、老人、肝肾功能异常和慢性病患者需要额外咨询医生或药师。',
  },
  {
    code: '03',
    title: '留意重复成分',
    text: '感冒药、退热药可能含有相同成分，重复使用会增加不良反应风险。',
  },
]

const quickSearch = async (text) => {
  keyword.value = text
  await searchMedicine()
}

const searchMedicine = async () => {
  if (!keyword.value.trim()) {
    alert('请输入药品名称或类别')
    return
  }

  loading.value = true
  medicines.value = []
  message.value = ''

  try {
    const response = await fetch(apiUrl('/api/medicine/search'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        keyword: keyword.value,
      }),
    })

    const data = await response.json()

    medicines.value = data.data || []
    message.value = data.message
  } catch (error) {
    message.value = '请求失败，请检查后端服务是否正常运行。'
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.medicine-page {
  display: grid;
  gap: 24px;
}

.medicine-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 34px;
  align-items: center;
  padding: clamp(24px, 4vw, 42px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.86)),
    var(--surface);
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: var(--radius-sm);
}

.eyebrow {
  margin-bottom: 10px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.medicine-hero h2 {
  color: var(--text-primary);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 900;
  line-height: 1.12;
}

.desc {
  max-width: 700px;
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.9;
}

.search-box {
  max-width: 760px;
  margin-top: 24px;
}

.search-label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-weight: 900;
}

.search-row {
  display: flex;
  gap: 12px;
  padding: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.search-row .ui-field {
  flex: 1;
  min-width: 0;
  font-size: 16px;
}

.search-row .ui-button {
  min-height: var(--control-height-lg);
}

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.quick-tag {
  min-height: 36px;
  padding: 0 12px;
  font-size: 13px;
}

.pharmacy-visual {
  min-height: 270px;
}

.shelf {
  height: 270px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid #cfe3ee;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}

.shelf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  color: var(--surface);
  background: linear-gradient(135deg, var(--pharmacy-teal), var(--clinical-green));
  border-radius: var(--radius-sm);
}

.shelf-header span,
.shelf-header strong {
  font-weight: 900;
}

.shelf-header strong {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: var(--pharmacy-teal);
  background: var(--surface);
  border-radius: var(--radius-sm);
}

.bottle-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 22px;
  padding-bottom: 18px;
  border-bottom: 8px solid #e2edf3;
}

.bottle-row i {
  position: relative;
  display: block;
  height: 92px;
  background: linear-gradient(180deg, #f8fafc 0 24%, #e0f2fe 24% 100%);
  border: 1px solid #cfe3ee;
  border-radius: 8px 8px 6px 6px;
}

.bottle-row i::before {
  position: absolute;
  top: -10px;
  left: 50%;
  width: 32px;
  height: 12px;
  content: "";
  background: #0f9f8e;
  border-radius: 5px 5px 2px 2px;
  transform: translateX(-50%);
}

.bottle-row i:nth-child(2)::before,
.bottle-row i:nth-child(4)::before {
  background: var(--medical-blue);
}

.bottle-row i:nth-child(3)::before {
  background: var(--medicine-amber);
}

.pill-strip {
  display: flex;
  gap: 10px;
  margin-top: 26px;
}

.pill-strip span {
  width: 54px;
  height: 22px;
  background: linear-gradient(90deg, #38bdf8 50%, var(--surface) 50%);
  border: 1px solid #c7dce8;
  border-radius: var(--radius-pill);
}

.pill-strip span:nth-child(2) {
  background: linear-gradient(90deg, #22c55e 50%, var(--surface) 50%);
}

.pill-strip span:nth-child(3) {
  background: linear-gradient(90deg, #f59e0b 50%, var(--surface) 50%);
}

.pill-strip span:nth-child(4) {
  background: linear-gradient(90deg, #f43f5e 50%, var(--surface) 50%);
}

.safety-panel {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.safety-panel article {
  padding: 20px;
}

.safety-panel span {
  display: inline-grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: var(--surface);
  background: var(--medicine-amber);
  border-radius: var(--radius-sm);
  font-weight: 900;
}

.safety-panel strong {
  display: block;
  margin-top: 14px;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 900;
}

.safety-panel p {
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.75;
}

.message {
  font-weight: 800;
}

.medicine-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.medicine-card {
  padding: 22px;
}

.medicine-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.medicine-label {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 900;
}

.medicine-card h3 {
  margin-top: 2px;
  color: var(--text-primary);
  font-size: 23px;
  font-weight: 900;
}

.medicine-card-header > strong {
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 900;
}

.field-grid {
  display: grid;
  gap: 12px;
}

.field-item {
  padding: 14px;
}

.field-grid strong {
  display: block;
  color: var(--medical-blue);
  font-weight: 900;
}

.field-grid span {
  display: block;
  margin-top: 6px;
  color: var(--text-secondary);
  line-height: 1.75;
}

.empty-state {
  border-style: dashed;
}

.empty-state strong {
  display: block;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.empty-state p {
  margin-top: 6px;
}

.notice strong {
  font-weight: 900;
}

@media (max-width: 980px) {
  .medicine-hero,
  .medicine-list,
  .safety-panel {
    grid-template-columns: 1fr;
  }

  .pharmacy-visual {
    max-width: 420px;
  }
}

@media (max-width: 620px) {
  .medicine-hero {
    padding: 22px;
  }

  .search-row {
    flex-direction: column;
  }

  .search-row .ui-button {
    width: 100%;
  }

  .medicine-card-header {
    flex-direction: column;
  }
}
</style>
