<template>
  <div class="home-page">
    <!-- Hero / Task Input Section -->
    <header class="hero-section" aria-labelledby="hero-title">
      <div class="hero-container">
        <h1 id="hero-title">有哪里不舒服？</h1>
        <p class="hero-subtitle">
          描述您的症状、持续时间以及身体情况，AI 医疗 Agent 将结合权威健康知识库为您智能整理参考建议。
        </p>

        <!-- Symptom query input card -->
        <div class="query-card-wrapper">
          <textarea
            v-model="homeQuestion"
            placeholder="例如：我最近总是头痛，晚上比较严重，还有一点鼻塞发热……"
            class="query-textarea"
            @keydown.enter.exact.prevent="startConsultation"
          ></textarea>

          <div class="query-action-row">
            <div class="action-tools">
              <button type="button" class="tool-btn" @click="goToChatWithAction('image')">
                <ImageIcon :size="16" aria-hidden="true" />
                <span>上传图片</span>
              </button>
              <button type="button" class="tool-btn" @click="goToChatWithAction('voice')">
                <Mic :size="16" aria-hidden="true" />
                <span>语音输入</span>
              </button>
            </div>

            <button type="button" class="start-btn" @click="startConsultation">
              <span>开始咨询</span>
              <ArrowRight :size="16" aria-hidden="true" />
            </button>
          </div>
        </div>

        <!-- Recommend questions -->
        <div class="recommend-questions">
          <span class="recommend-label">您可以试着问：</span>
          <div class="recommend-list">
            <button
              v-for="q in recommendedQuestions"
              :key="q"
              type="button"
              class="recommend-pill"
              @click="handleRecommendClick(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <!-- Trust indicators -->
        <div class="trust-indicators">
          <div class="trust-item">
            <ShieldCheck :size="16" aria-hidden="true" />
            <span>危险症状优先分诊</span>
          </div>
          <div class="trust-item">
            <BookOpen :size="16" aria-hidden="true" />
            <span>基于知识库可靠检索</span>
          </div>
          <div class="trust-item">
            <AlertTriangle :size="16" aria-hidden="true" />
            <span>本回答不替代专业诊疗</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Features / Category Cards -->
    <main class="main-content">
      <section class="features-section" aria-label="核心服务功能">
        <h2 class="section-title">核心辅助功能</h2>
        <div class="features-grid">
          <article class="feature-card" @click="router.push('/chat')">
            <div class="feature-icon-wrap message-wrap">
              <MessageSquare :size="24" aria-hidden="true" />
            </div>
            <h3>AI 症状咨询</h3>
            <p>通过对话描述身体不适或既往病史，获得结构化分析建议、潜在原因与就医指引。</p>
            <div class="feature-link">
              <span>立即体验</span>
              <ArrowRight :size="16" aria-hidden="true" />
            </div>
          </article>

          <article class="feature-card" @click="router.push('/knowledge')">
            <div class="feature-icon-wrap pills-wrap">
              <Pill :size="24" aria-hidden="true" />
            </div>
            <h3>药品信息查询</h3>
            <p>快速核对常见药品的适用症、用法用量、特殊人群禁忌与常见不良反应说明。</p>
            <div class="feature-link">
              <span>浏览知识库</span>
              <ArrowRight :size="16" aria-hidden="true" />
            </div>
          </article>

          <article class="feature-card" @click="goToChatWithAction('image')">
            <div class="feature-icon-wrap camera-wrap">
              <Camera :size="24" aria-hidden="true" />
            </div>
            <h3>图片辅助识别</h3>
            <p>支持上传药盒包装照片、检验检查单或局部症状照片，作为 AI 调度台的线索输入。</p>
            <div class="feature-link">
              <span>去上传</span>
              <ArrowRight :size="16" aria-hidden="true" />
            </div>
          </article>

          <article class="feature-card" @click="router.push('/analytics')">
            <div class="feature-icon-wrap analytics-wrap">
              <BarChart2 :size="24" aria-hidden="true" />
            </div>
            <h3>数据分析</h3>
            <p>查看咨询趋势、风险提示、知识库命中与用户反馈，快速了解系统运行与服务质量。</p>
            <div class="feature-link">
              <span>查看分析</span>
              <ArrowRight :size="16" aria-hidden="true" />
            </div>
          </article>
        </div>
      </section>

      <!-- Security Notice -->
      <section class="notice-section">
        <strong>安全声明：</strong>
        本系统所包含的疾病常识、药品常识和 AI 生成的健康分析意见均仅作为信息参考，不构成医疗诊断或具体的用药指导。如果您的症状较为严重或持续恶化，请务必立即就医或联系急救服务。
      </section>

    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ShieldCheck,
  BookOpen,
  AlertTriangle,
  MessageSquare,
  Pill,
  Camera,
  ArrowRight,
  Mic,
  Image as ImageIcon,
  BarChart2,
} from '@lucide/vue'

const router = useRouter()
const homeQuestion = ref('')

const recommendedQuestions = [
  '最近总是头痛怎么办？',
  '布洛芬饭前还是饭后吃？',
  '感冒和过敏性鼻炎怎么区分？',
  '儿童发热应该注意什么？',
]

const startConsultation = () => {
  const text = homeQuestion.value.trim()
  if (!text) return
  sessionStorage.setItem('home_pending_question', text)
  router.push('/chat')
}

const handleRecommendClick = (questionText) => {
  sessionStorage.setItem('home_pending_question', questionText)
  router.push('/chat')
}

const goToChatWithAction = () => {
  // Direct routes to chat where the composer will get focused
  router.push('/chat')
}

</script>

<style scoped>
.home-page {
  display: grid;
  gap: 36px;
}

/* Hero Section with Search bar */
.hero-section {
  display: flex;
  justify-content: center;
  padding: 48px 24px;
  background:
    radial-gradient(circle at 10% 20%, rgba(37, 99, 235, 0.04), transparent 40%),
    radial-gradient(circle at 90% 80%, rgba(13, 148, 136, 0.04), transparent 45%);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  background-color: #ffffff;
}

.hero-container {
  max-width: 800px;
  width: 100%;
  text-align: center;
}

#hero-title {
  font-size: clamp(32px, 5vw, 44px);
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.hero-subtitle {
  margin-top: 14px;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-secondary);
  max-width: 620px;
  margin-left: auto;
  margin-right: auto;
}

/* Query card layout */
.query-card-wrapper {
  margin-top: 32px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: var(--shadow-md);
  padding: 14px 16px 12px;
  display: flex;
  flex-direction: column;
  text-align: left;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.query-card-wrapper:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.query-textarea {
  width: 100%;
  min-height: 72px;
  border: none;
  outline: none;
  resize: none;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-primary);
}

.query-textarea::placeholder {
  color: var(--text-muted);
}

.query-action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.action-tools {
  display: flex;
  gap: 8px;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tool-btn:hover {
  background: var(--primary-soft);
  color: var(--primary);
  border-color: var(--primary);
}

.start-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 18px;
  background: var(--primary);
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.start-btn:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

/* Recommend Questions */
.recommend-questions {
  margin-top: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13.5px;
  text-align: left;
}

.recommend-label {
  color: var(--text-muted);
  font-weight: 600;
}

.recommend-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.recommend-pill {
  padding: 6px 12px;
  background: var(--surface-soft);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.recommend-pill:hover {
  background: var(--primary-soft);
  color: var(--primary);
  border-color: var(--primary);
}

/* Trust Indicators */
.trust-indicators {
  margin-top: 36px;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 24px;
  border-top: 1px solid var(--border);
  padding-top: 20px;
}

.trust-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  color: var(--text-muted);
  font-weight: 700;
}

.trust-item svg {
  color: var(--teal);
}

/* Main Content Page */
.main-content {
  display: flex;
  flex-direction: column;
  gap: 36px;
}

/* Features Grid */
.features-section {
  display: grid;
  gap: 20px;
}

.section-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.feature-card {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--shadow-sm);
}

.feature-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary);
}

.feature-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  margin-bottom: 20px;
}

.message-wrap {
  background: #eff6ff;
  color: var(--primary);
}

.pills-wrap {
  background: #f0fdfa;
  color: var(--teal);
}

.camera-wrap {
  background: #f0fdfa;
  color: var(--teal);
}

.analytics-wrap {
  color: #7c3aed;
  background: #f5f3ff;
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.feature-card p {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 24px;
  flex: 1;
}

.feature-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 800;
  color: var(--primary);
  margin-top: auto;
}

.feature-card:hover .feature-link {
  color: var(--primary-hover);
}

/* Notice Warning */
.notice-section {
  padding: 16px 20px;
  background: var(--warning-soft);
  color: var(--warning-text);
  border: 1px solid var(--warning-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.7;
}

@media (max-width: 1050px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .features-grid {
    grid-template-columns: 1fr;
  }

  .query-action-row {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .action-tools {
    justify-content: space-between;
  }
  .start-btn {
    justify-content: center;
  }
  .trust-indicators {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
