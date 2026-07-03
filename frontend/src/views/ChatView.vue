<template>
  <div class="page">
    <div class="page-title">
      <h2>症状自查</h2>
      <p>
        请输入你的症状描述，系统会先进行危险症状识别，再匹配数据库记录并结合常见病知识库RAG检索，
        返回可能相关疾病方向、日常护理建议、用药注意事项和就医提醒。
      </p>
    </div>

    <div class="panel">
      <label class="label">症状描述</label>

      <textarea
        v-model="question"
        placeholder="例如：我咳嗽、流鼻涕、喉咙痛，怎么办？"
      ></textarea>

      <div class="example-list">
        <span @click="fillExample('我咳嗽、流鼻涕、喉咙痛，怎么办？')">
          咳嗽、流鼻涕、喉咙痛
        </span>
        <span @click="fillExample('我肚子疼，还一直拉肚子，怎么办？')">
          肚子疼、拉肚子
        </span>
        <span @click="fillExample('我皮肤起红疹，很痒，怎么办？')">
          皮肤红疹、瘙痒
        </span>
        <span @click="fillExample('我胸痛，而且喘不上气，怎么办？')">
          胸痛、喘不上气
        </span>
      </div>

      <button @click="submitQuestion" :disabled="loading">
        {{ loading ? '分析中...' : '开始自查' }}
      </button>
    </div>

    <div v-if="warning && warning.has_warning" class="warning-box">
      <h3>危险症状提醒</h3>
      <p>{{ warning.message }}</p>
      <div class="tag-list">
        <span v-for="(item, index) in warning.matched" :key="index">
          {{ item }}
        </span>
      </div>
    </div>

    <div v-if="answer" class="result">
      <h3>系统回答</h3>

      <div v-if="llmInfo" class="llm-status">
        <div v-if="llmInfo.used" class="llm-success">
          DeepSeek 大模型已参与生成，模型：{{ llmInfo.model }}
        </div>

        <div v-else class="llm-fallback">
          大模型未启用，当前使用本地模板回答。
          <br />
          原因：{{ llmInfo.error }}
        </div>
      </div>

      <pre>{{ answer }}</pre>

      <div v-if="historyId" class="feedback-panel">
        <div class="feedback-heading">
          <div>
            <strong>评价本次回答</strong>
            <span>点击星级后，可以补充具体意见。</span>
          </div>

          <div class="star-rating" aria-label="五星评价">
            <button
              v-for="star in 5"
              :key="star"
              type="button"
              :class="{ active: star <= feedbackRating }"
              @click="feedbackRating = star"
            >
              ★
            </button>
          </div>
        </div>

        <textarea
          v-model="feedbackText"
          class="feedback-textarea"
          placeholder="可以写下哪里准确、哪里不够清楚，或希望系统补充什么。"
        ></textarea>

        <div class="feedback-actions">
          <button type="button" @click="submitFeedback" :disabled="feedbackLoading || !feedbackRating">
            {{ feedbackLoading ? '提交中...' : '提交评价' }}
          </button>
          <span v-if="feedbackMessage">{{ feedbackMessage }}</span>
        </div>
      </div>
    </div>

    <div v-if="hasDatabaseMatches" class="docs database-docs">
      <h3>数据库命中的结构化记录</h3>

      <div v-if="databaseDiseases.length > 0" class="database-group">
        <h4>疾病记录</h4>

        <div v-for="(item, index) in databaseDiseases" :key="`disease-${index}`" class="doc-card">
          <div class="doc-header">
            <div>
              <strong>{{ index + 1 }}. {{ item.title }}</strong>
              <span class="doc-type">常见病</span>
            </div>

            <span class="score">匹配分：{{ item.score }}</span>
          </div>

          <div class="matched-list">
            <span v-for="(match, matchIndex) in item.matched_fields" :key="matchIndex">
              {{ match }}
            </span>
          </div>

          <p class="doc-content">
            常见症状：{{ (item.raw && item.raw.symptoms || []).join('、') }}
            <br />
            {{ item.raw && item.raw.description }}
          </p>
        </div>
      </div>

      <div v-if="databaseMedicines.length > 0" class="database-group">
        <h4>药品记录</h4>

        <div v-for="(item, index) in databaseMedicines" :key="`medicine-${index}`" class="doc-card">
          <div class="doc-header">
            <div>
              <strong>{{ index + 1 }}. {{ item.title }}</strong>
              <span class="doc-type">药品</span>
            </div>

            <span class="score">匹配分：{{ item.score }}</span>
          </div>

          <div class="matched-list">
            <span v-for="(match, matchIndex) in item.matched_fields" :key="matchIndex">
              {{ match }}
            </span>
          </div>

          <p class="doc-content">
            适用情况：{{ item.raw && item.raw.usage }}
            <br />
            注意事项：{{ item.raw && item.raw.notice }}
          </p>
        </div>
      </div>
    </div>

    <div v-if="retrievedDocs.length > 0" class="docs">
      <h3>RAG检索到的相关知识</h3>

      <div v-for="(doc, index) in retrievedDocs" :key="index" class="doc-card">
        <div class="doc-header">
          <div>
            <strong>{{ index + 1 }}. {{ doc.title }}</strong>
            <span class="doc-type">
              {{ doc.doc_type === 'disease' ? '常见病' : '药品' }}
            </span>
          </div>

          <span class="score">相似度：{{ doc.score.toFixed(4) }}</span>
        </div>

        <div v-if="doc.citation || doc.source" class="citation">
          来源：{{ doc.citation || (doc.source && doc.source.label) }}
        </div>

        <p class="doc-content">{{ doc.content }}</p>
      </div>
    </div>

    <div class="notice">
      <strong>安全提示：</strong>
      本系统仅提供健康信息参考，不能替代医生诊断或药师指导。
      如症状严重、持续加重，或出现呼吸困难、胸痛、高热不退等情况，请及时就医。
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { apiUrl } from '../api'

const question = ref('')
const answer = ref('')
const retrievedDocs = ref([])
const databaseContext = ref({
  diseases: [],
  medicines: [],
  has_matches: false,
})
const warning = ref(null)
const llmInfo = ref(null)
const loading = ref(false)
const historyId = ref(null)
const feedbackRating = ref(0)
const feedbackText = ref('')
const feedbackMessage = ref('')
const feedbackLoading = ref(false)

const fillExample = (text) => {
  question.value = text
}

const databaseDiseases = computed(() => databaseContext.value?.diseases || [])
const databaseMedicines = computed(() => databaseContext.value?.medicines || [])
const hasDatabaseMatches = computed(() => (
  databaseDiseases.value.length > 0 || databaseMedicines.value.length > 0
))

const submitQuestion = async () => {
  if (!question.value.trim()) {
    alert('请输入症状描述')
    return
  }

  loading.value = true
  answer.value = ''
  retrievedDocs.value = []
  databaseContext.value = {
    diseases: [],
    medicines: [],
    has_matches: false,
  }
  warning.value = null
  llmInfo.value = null
  historyId.value = null
  feedbackRating.value = 0
  feedbackText.value = ''
  feedbackMessage.value = ''

  try {
    const response = await fetch(apiUrl('/api/chat'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: question.value,
      }),
    })

    const data = await response.json()

    answer.value = data.answer
    retrievedDocs.value = data.retrieved_docs || []
    databaseContext.value = data.database_context || {
      diseases: [],
      medicines: [],
      has_matches: false,
    }
    warning.value = data.warning || null
    llmInfo.value = data.llm || null
    historyId.value = data.history_id || null
  } catch (error) {
    answer.value = '请求失败，请检查后端服务是否正常运行。'
    console.error(error)
  } finally {
    loading.value = false
  }
}

const submitFeedback = async () => {
  if (!historyId.value || !feedbackRating.value) {
    feedbackMessage.value = '请先选择星级'
    return
  }

  feedbackLoading.value = true
  feedbackMessage.value = ''

  try {
    const response = await fetch(apiUrl(`/api/history/${historyId.value}/feedback`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        rating: feedbackRating.value,
        feedback_text: feedbackText.value,
      }),
    })

    const data = await response.json()
    feedbackMessage.value = data.message || '评价已保存'
  } catch (error) {
    feedbackMessage.value = '评价提交失败，请检查后端服务是否正常运行。'
    console.error(error)
  } finally {
    feedbackLoading.value = false
  }
}
</script>

<style scoped>
.page-title {
  margin-bottom: 24px;
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

.panel {
  background: white;
  padding: 26px;
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.label {
  display: block;
  margin-bottom: 10px;
  font-weight: 700;
  color: #374151;
}

textarea {
  width: 100%;
  height: 150px;
  resize: vertical;
  padding: 16px;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  font-size: 16px;
  outline: none;
  box-sizing: border-box;
  line-height: 1.7;
}

textarea:focus {
  border-color: #2563eb;
}

.example-list {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.example-list span {
  background: #eff6ff;
  color: #2563eb;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 14px;
}

.example-list span:hover {
  background: #dbeafe;
}

button {
  margin-top: 18px;
  padding: 12px 26px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
}

button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.warning-box {
  margin-top: 24px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(127, 29, 29, 0.08);
}

.warning-box h3 {
  margin-bottom: 10px;
}

.warning-box p {
  line-height: 1.8;
}

.tag-list {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tag-list span {
  background: #dc2626;
  color: white;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 13px;
}

.result,
.docs {
  margin-top: 24px;
  background: white;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.result h3,
.docs h3 {
  margin-bottom: 14px;
  color: #111827;
}

pre {
  white-space: pre-wrap;
  line-height: 1.9;
  font-size: 15px;
  color: #374151;
  font-family: "Microsoft YaHei", Arial, sans-serif;
}

.doc-card {
  border: 1px solid #e5e7eb;
  padding: 18px;
  border-radius: 14px;
  margin-top: 14px;
  background: #f9fafb;
}

.doc-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 10px;
}

.doc-type {
  margin-left: 8px;
  font-size: 12px;
  color: white;
  background: #2563eb;
  padding: 3px 8px;
  border-radius: 999px;
}

.score {
  font-size: 13px;
  color: #6b7280;
}

.citation {
  margin-bottom: 8px;
  color: #0f766e;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

.doc-content {
  color: #4b5563;
  line-height: 1.8;
  white-space: pre-wrap;
}

.database-docs {
  border: 1px solid #bfdbfe;
}

.database-group + .database-group {
  margin-top: 20px;
}

.database-group h4 {
  margin: 16px 0 8px;
  color: #1f2937;
  font-size: 16px;
}

.matched-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.matched-list span {
  background: #ecfeff;
  color: #0f766e;
  border: 1px solid #99f6e4;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
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

.llm-status {
  margin-bottom: 14px;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.7;
}

.llm-success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  padding: 10px 14px;
  border-radius: 10px;
  font-weight: 600;
}

.llm-fallback {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  padding: 10px 14px;
  border-radius: 10px;
  font-weight: 600;
}

.feedback-panel {
  display: grid;
  gap: 14px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #e5e7eb;
}

.feedback-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.feedback-heading strong,
.feedback-heading span {
  display: block;
}

.feedback-heading strong {
  color: #111827;
  font-weight: 800;
}

.feedback-heading span {
  margin-top: 3px;
  color: #6b7280;
  font-size: 13px;
}

.star-rating {
  display: flex;
  gap: 4px;
}

.star-rating button {
  margin-top: 0;
  width: 38px;
  height: 38px;
  padding: 0;
  color: #cbd5e1;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 22px;
  line-height: 1;
}

.star-rating button.active {
  color: #d97706;
  background: #fff7ed;
  border-color: #fed7aa;
}

.feedback-textarea {
  min-height: 92px;
  height: auto;
  resize: vertical;
}

.feedback-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.feedback-actions button {
  margin-top: 0;
}

.feedback-actions span {
  color: #0f766e;
  font-weight: 700;
}

@media (max-width: 640px) {
  .feedback-heading {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
