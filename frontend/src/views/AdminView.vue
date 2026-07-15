<template>
  <div v-if="!isAdmin" class="access-gate">
    <p class="eyebrow">ADMIN ONLY</p>
    <h2>需要管理员登录</h2>
    <p>管理员后台包含知识库写入、向量索引更新和问答审核操作，请先使用管理员账号登录。</p>
    <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
    <RouterLink to="/login">去登录</RouterLink>
  </div>

  <div v-else class="admin-page">
    <section class="admin-hero">
      <div>
        <p class="eyebrow">ADMIN CONSOLE</p>
        <h2>管理员后台</h2>
        <p>
          这里只处理复核样本、知识库维护、用户权限和系统更新；运行统计统一在数据分析页面查看。
        </p>
      </div>

      <div class="admin-actions">
        <button type="button" @click="loadAdminData(true)" :disabled="loading">
          {{ loading ? '刷新中...' : '刷新当前分区' }}
        </button>
      </div>
    </section>

    <nav class="admin-section-tabs" aria-label="管理后台分区">
      <button
        v-for="section in adminSections"
        :key="section.value"
        type="button"
        :class="{ active: activeAdminSection === section.value }"
        @click="selectAdminSection(section.value)"
      >
        {{ section.label }}
      </button>
    </nav>

    <section v-if="activeAdminSection === 'overview'" class="overview-dashboard">
      <div class="metric-grid">
        <article>
          <strong>{{ users.length }}</strong>
          <span>系统用户</span>
        </article>
        <article>
          <strong>{{ knowledge.knowledge.disease_count }}</strong>
          <span>疾病知识</span>
        </article>
        <article>
          <strong>{{ knowledge.knowledge.medicine_count }}</strong>
          <span>药品说明</span>
        </article>
        <article>
          <strong>{{ knowledge.knowledge.warning_rule_count }}</strong>
          <span>危险规则</span>
        </article>
        <article>
          <strong>{{ historyList.length }}</strong>
          <span>问答记录</span>
        </article>
      </div>

      <div class="overview-insights">
        <article>
          <div>
            <span>待复核样本</span>
            <strong>{{ issueStatusCount('pending') }}</strong>
          </div>
          <p>需要管理员复核、补知识库或判断是否忽略。</p>
        </article>
        <article>
          <div>
            <span>低置信 Agent</span>
            <strong>{{ lowConfidenceRuns.length }}</strong>
          </div>
          <p>近期回答可靠性偏低，适合优先检查 RAG 召回和工具调度。</p>
        </article>
        <article>
          <div>
            <span>无召回记录</span>
            <strong>{{ noRetrievalRuns.length }}</strong>
          </div>
          <p>说明用户问题没有匹配到知识库，可作为后续补充方向。</p>
        </article>
        <article>
          <div>
            <span>视觉输入</span>
            <strong>{{ visualRuns.length }}</strong>
          </div>
          <p>反映图片/视频输入是否真正进入多模态 Agent 流程。</p>
        </article>
      </div>

    </section>

    <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>

    <section v-if="activeAdminSection === 'agent'" class="agent-log-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">AGENT OBSERVABILITY</p>
          <h3>Agent 调度监控</h3>
          <span class="section-help">
            汇总最近 Agent 运行中的低置信、无 RAG 召回、视觉输入和文本大模型调用，便于定位调度链路问题。
          </span>
        </div>
      </div>

      <div class="agent-observe-summary">
        <article>
          <strong>{{ lowConfidenceRuns.length }}</strong>
          <span>最近低置信回答</span>
        </article>
        <article>
          <strong>{{ noRetrievalRuns.length }}</strong>
          <span>最近无 RAG 召回</span>
        </article>
        <article>
          <strong>{{ visualRuns.length }}</strong>
          <span>最近视觉输入</span>
        </article>
        <article>
          <strong>{{ llmRuns.length }}</strong>
          <span>文本大模型调用</span>
        </article>
      </div>

      <div class="agent-log-grid">
        <article>
          <div class="mini-heading">
            <strong>最近会话</strong>
            <span>{{ conversationSessions.length }} 条</span>
          </div>

          <div v-if="conversationSessions.length === 0" class="empty-state">
            暂无多轮会话记录。
          </div>

          <div v-else class="mini-list">
            <div v-for="item in conversationSessions.slice(0, 5)" :key="item.id" class="mini-row">
              <strong>{{ item.title }}</strong>
              <span>会话 #{{ item.id }} · 消息 {{ item.message_count }} · 用户 {{ item.user_id || '未登录' }}</span>
            </div>
          </div>
        </article>

        <article>
          <div class="mini-heading">
            <strong>最近低置信回答</strong>
            <span>{{ lowConfidenceRuns.length }} 条</span>
          </div>

          <div v-if="lowConfidenceRuns.length === 0" class="empty-state">
            暂无低置信记录。
          </div>

          <div v-else class="mini-list">
            <div v-for="item in lowConfidenceRuns.slice(0, 5)" :key="`low-${item.id}`" class="mini-row">
              <strong>{{ labelAction(item.action) }} / {{ labelIntent(item.intent) }}</strong>
              <span>
                运行 #{{ item.id }} · 可靠性 {{ formatPercent(item.confidence) }} · {{ item.created_at }}
              </span>
            </div>
          </div>
        </article>

        <article>
          <div class="mini-heading">
            <strong>最近无 RAG 召回</strong>
            <span>{{ noRetrievalRuns.length }} 条</span>
          </div>

          <div v-if="noRetrievalRuns.length === 0" class="empty-state">
            暂无无召回记录。
          </div>

          <div v-else class="mini-list">
            <div v-for="item in noRetrievalRuns.slice(0, 5)" :key="`norag-${item.id}`" class="mini-row">
              <strong>{{ labelAction(item.action) }} / {{ labelIntent(item.intent) }}</strong>
              <span>运行 #{{ item.id }} · 会话 #{{ item.session_id }} · 工具 {{ formatTools(item.tool_names) }}</span>
            </div>
          </div>
        </article>

        <article>
          <div class="mini-heading">
            <strong>最近视觉模型输入</strong>
            <span>{{ visualRuns.length }} 条</span>
          </div>

          <div v-if="visualRuns.length === 0" class="empty-state">
            暂无图片或视频输入记录。
          </div>

          <div v-else class="mini-list">
            <div v-for="item in visualRuns.slice(0, 5)" :key="`visual-${item.id}`" class="mini-row">
              <strong>{{ labelInputType(item.multimodal_input?.input_type) }} · {{ labelAction(item.action) }}</strong>
              <span>{{ compactText(item.multimodal_input?.image_summary || item.multimodal_input?.text_content, 54) }}</span>
            </div>
          </div>
        </article>

        <article>
          <div class="mini-heading">
            <strong>最近文本大模型调用</strong>
            <span>{{ llmRuns.length }} 条</span>
          </div>

          <div v-if="llmRuns.length === 0" class="empty-state">
            暂无文本大模型调用记录。
          </div>

          <div v-else class="mini-list">
            <div v-for="item in llmRuns.slice(0, 5)" :key="`llm-${item.id}`" class="mini-row">
              <strong>{{ item.llm_model || '已调用文本大模型' }}</strong>
              <span>{{ item.llm_provider || 'provider 未记录' }} · 运行 #{{ item.id }} · {{ labelAction(item.action) }}</span>
            </div>
          </div>
        </article>
      </div>

      <div class="agent-run-table">
        <div class="mini-heading">
          <strong>Agent 决策链详情</strong>
          <span>{{ agentRuns.length }} 条</span>
        </div>

        <div v-if="agentRuns.length === 0" class="empty-state">
          暂无 Agent 调度日志。
        </div>

        <details v-for="item in pagedAgentRuns" v-else :key="`detail-${item.id}`" class="agent-run-detail">
          <summary>
            <div>
              <strong>{{ labelAction(item.action) }} / {{ labelIntent(item.intent) }}</strong>
              <span>运行 #{{ item.id }} · 会话 #{{ item.session_id }} · {{ item.created_at }}</span>
            </div>
            <div class="agent-chip-row">
              <span :class="['agent-chip', item.flags?.used_rag ? 'ok' : 'muted']">RAG {{ item.flags?.used_rag ? '已调用' : '未调用' }}</span>
              <span :class="['agent-chip', item.flags?.used_image ? 'ok' : 'muted']">图片 {{ item.flags?.used_image ? '已参与' : '未参与' }}</span>
              <span :class="['agent-chip', item.flags?.used_medicine ? 'ok' : 'muted']">药品库 {{ item.flags?.used_medicine ? '已调用' : '未调用' }}</span>
              <span :class="['agent-chip', item.flags?.used_llm ? 'ok' : 'muted']">文本模型 {{ item.flags?.used_llm ? '已调用' : '未调用' }}</span>
              <span :class="['agent-chip', item.flags?.low_confidence ? 'warn' : 'ok']">可靠性 {{ formatPercent(item.confidence) }}</span>
            </div>
          </summary>

          <div class="agent-detail-body">
            <div class="agent-detail-grid">
              <div>
                <span>工具链</span>
                <strong>{{ formatTools(item.tool_names) || '未记录' }}</strong>
              </div>
              <div>
                <span>召回文档</span>
                <strong>{{ item.metrics?.retrieval_doc_count || 0 }} 条 · 最高分 {{ item.metrics?.retrieval_top_score || 0 }}</strong>
              </div>
              <div>
                <span>大模型</span>
                <strong>{{ item.flags?.used_llm ? `${item.llm_provider || 'provider'} / ${item.llm_model || 'model'}` : '未调用' }}</strong>
              </div>
            </div>

            <div v-if="item.steps?.length" class="agent-step-list">
              <div v-for="step in item.steps" :key="`${item.id}-${step.index}-${step.name}`">
                <b>{{ step.index }}. {{ labelTool(step.name) }}</b>
                <span>{{ step.status || 'done' }}</span>
              </div>
            </div>

            <p v-if="item.trace?.summary || item.trace?.reason" class="agent-reason">
              {{ item.trace.summary || item.trace.reason }}
            </p>
          </div>
        </details>

        <div v-if="agentRuns.length" class="pagination-bar">
          <span>{{ pageRangeLabel(agentRuns.length, 'agent') }}</span>
          <label>
            每页
            <select v-model.number="pagination.agent.pageSize" @change="resetPage('agent')">
              <option v-for="size in pageSizeOptions" :key="`agent-${size}`" :value="size">{{ size }}</option>
            </select>
          </label>
          <button type="button" class="ghost-btn" :disabled="currentPage(agentRuns.length, 'agent') <= 1" @click="changePage('agent', agentRuns.length, -1)">
            上一页
          </button>
          <button type="button" class="ghost-btn" :disabled="currentPage(agentRuns.length, 'agent') >= pageCount(agentRuns.length, 'agent')" @click="changePage('agent', agentRuns.length, 1)">
            下一页
          </button>
        </div>
      </div>
    </section>

    <section v-if="activeAdminSection === 'review'" class="review-workbench">
      <div class="section-title">
        <div>
          <p class="eyebrow">REVIEW WORKFLOW</p>
          <h3>回答复核样本</h3>
          <span class="section-help">
            有问题特征的回答默认进入待处理；小标签说明原因，重新测试后再标记已处理或忽略。
          </span>
        </div>

        <div class="tabs">
          <button
            v-for="filter in reviewFilters"
            :key="filter.value"
            type="button"
            :class="{ active: activeReviewFilter === filter.value }"
            @click="setReviewFilter(filter.value)"
          >
            {{ filter.label }}
          </button>
        </div>
      </div>

      <div class="review-summary">
        <article>
          <strong>{{ issueStatusCount('pending') }}</strong>
          <span>待处理样本</span>
        </article>
        <article>
          <strong>{{ issueStatusCount('processed') }}</strong>
          <span>已处理</span>
        </article>
        <article>
          <strong>{{ issueStatusCount('ignored') }}</strong>
          <span>已忽略</span>
        </article>
        <article>
          <strong>{{ issueList.length }}</strong>
          <span>样本总数</span>
        </article>
      </div>

      <div class="review-toolbar">
        <span>当前筛选：{{ reviewFilterLabel(activeReviewFilter) }}，共 {{ filteredIssues.length }} 条</span>
        <button type="button" class="ghost-btn" @click="loadReviewIssues">
          刷新样本
        </button>
      </div>

      <div v-if="filteredIssues.length === 0" class="empty-state">
        当前筛选下暂无复核样本。
      </div>

      <div v-else class="issue-list">
        <article v-for="item in pagedIssues" :key="item.record_id" class="issue-card">
          <div class="issue-head">
            <div class="issue-title-block">
              <div class="issue-badges">
                <span :class="['issue-tag', issueTagClass(item.issue_type)]">
                  {{ item.issue_type }}
                </span>
                <span :class="['ticket-status', item.review_status || 'pending']">
                  {{ reviewStatusLabel(item.review_status) }}
                </span>
              </div>
              <strong>{{ item.keyword || '待补充条目' }}</strong>
            </div>
            <small>{{ item.create_time }}</small>
          </div>

          <section class="issue-section">
            <div class="issue-section-title">用户问题</div>
            <p class="issue-question">{{ item.question }}</p>

            <details class="issue-answer">
              <summary>查看原回答</summary>
              <pre>{{ item.answer }}</pre>
            </details>
          </section>

          <section class="issue-section">
            <div class="issue-section-title">问题特征</div>
            <div class="issue-meta">
              <span>可靠性：{{ Math.round((item.confidence || 0) * 100) }}%</span>
              <span>检索数：{{ item.retrieved_count }}</span>
              <span>最高分：{{ item.top_score }}</span>
              <span v-if="item.action">动作：{{ labelAction(item.action) }}</span>
            </div>

            <p class="issue-fix">{{ item.suggested_fix }}</p>
            <div class="issue-notes">
              <p v-if="item.feedback_text" class="feedback-note">用户反馈：{{ item.feedback_text }}</p>
              <p v-if="item.error_reason" class="feedback-note">管理员标注：{{ item.error_reason }}</p>
              <p v-if="item.review_note" class="feedback-note">处理备注：{{ item.review_note }}</p>
            </div>
          </section>

          <div v-if="currentReviewRetest(item)" class="retest-result">
            <div class="mini-heading">
              <strong>当前系统测试结果</strong>
              <span>{{ labelAction(currentReviewRetest(item).current.action) }}</span>
            </div>
            <div class="retest-metrics">
              <span>
                可靠性 {{ formatPercent(currentReviewRetest(item).previous.confidence) }}
                → {{ formatPercent(currentReviewRetest(item).current.confidence) }}
              </span>
              <span>
                最高分 {{ currentReviewRetest(item).previous.top_score }}
                → {{ currentReviewRetest(item).current.top_score }}
              </span>
              <span>召回 {{ currentReviewRetest(item).current.retrieved_count }} 条</span>
              <span>{{ labelRetestContext(currentReviewRetest(item).context) }}</span>
              <span v-if="currentReviewRetest(item).retested_at">复测时间 {{ currentReviewRetest(item).retested_at }}</span>
            </div>
            <p v-if="currentReviewRetest(item).current.retrieved_titles?.length">
              当前召回：{{ currentReviewRetest(item).current.retrieved_titles.join('、') }}
            </p>
            <pre>{{ currentReviewRetest(item).current.answer }}</pre>
          </div>

          <section class="issue-section issue-process">
            <div class="issue-section-title">处理操作</div>
            <textarea
              v-model="reviewNotes[item.record_id]"
              class="review-note-input"
              rows="2"
              placeholder="填写处理说明，例如：已补充知识并用原问题复测通过"
            ></textarea>

            <div class="issue-actions">
              <button
                type="button"
                class="retest-btn"
                :disabled="isReviewRetesting(item) || isReviewUpdating(item)"
                @click="retestReviewTicket(item)"
              >
                {{ isReviewRetesting(item) ? '测试中...' : '重新测试' }}
              </button>
              <button
                type="button"
                class="ghost-btn"
                :disabled="isReviewUpdating(item) || item.review_status === 'processed' || !String(reviewNotes[item.record_id] || '').trim()"
                @click="updateReviewTicket(item, 'processed')"
              >
                {{ isReviewUpdating(item, 'processed') ? '处理中...' : '标记已处理' }}
              </button>
              <button
                type="button"
                class="invalid-btn"
                :disabled="isReviewUpdating(item) || item.review_status === 'ignored' || !String(reviewNotes[item.record_id] || '').trim()"
                @click="updateReviewTicket(item, 'ignored')"
              >
                {{ isReviewUpdating(item, 'ignored') ? '处理中...' : '忽略样本' }}
              </button>
            </div>
          </section>
        </article>
      </div>

      <div v-if="filteredIssues.length" class="pagination-bar">
        <span>{{ pageRangeLabel(filteredIssues.length, 'issues') }}</span>
        <label>
          每页
          <select v-model.number="pagination.issues.pageSize" @change="resetPage('issues')">
            <option v-for="size in pageSizeOptions" :key="`issues-${size}`" :value="size">{{ size }}</option>
          </select>
        </label>
        <button type="button" class="ghost-btn" :disabled="currentPage(filteredIssues.length, 'issues') <= 1" @click="changePage('issues', filteredIssues.length, -1)">
          上一页
        </button>
        <button type="button" class="ghost-btn" :disabled="currentPage(filteredIssues.length, 'issues') >= pageCount(filteredIssues.length, 'issues')" @click="changePage('issues', filteredIssues.length, 1)">
          下一页
        </button>
      </div>
    </section>

    <section v-if="activeAdminSection === 'users'" class="user-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">USER PERMISSIONS</p>
          <h3>用户权限管理</h3>
          <span class="section-help">
            搜索用户后点击“编辑”调整角色、启停状态或重置密码，避免用户数量增加后列表过于拥挤。
          </span>
        </div>
      </div>

      <div class="user-toolbar">
        <label class="user-search">
          搜索用户
          <input v-model="userSearch" placeholder="输入用户名或角色" />
        </label>

        <button type="button" @click="openCreateUserModal">
          新建用户
        </button>
      </div>

      <div class="user-table compact-table">
        <div class="user-table-head">
          <span>用户名</span>
          <span>角色</span>
          <span>状态</span>
          <span>创建时间</span>
          <span>操作</span>
        </div>

        <div v-if="filteredUsers.length === 0" class="empty-state">
          没有匹配的用户。
        </div>

        <article v-for="item in pagedUsers" v-else :key="item.username" class="user-row">
          <strong>{{ item.username }}</strong>
          <span>{{ roleLabel(item.role) }}</span>
          <span :class="['user-state', item.active === false ? 'disabled' : 'enabled']">
            {{ item.active === false ? '已停用' : '启用中' }}
          </span>
          <span>{{ item.create_time || '未记录' }}</span>
          <div class="user-actions">
            <button type="button" class="ghost-btn" @click="openEditUserModal(item)">
              编辑
            </button>
            <button
              class="delete-user"
              type="button"
              @click="deleteSystemUser(item.username)"
              :disabled="item.username === user?.username"
            >
              删除
            </button>
          </div>
        </article>
      </div>

      <div v-if="filteredUsers.length" class="pagination-bar">
        <span>{{ pageRangeLabel(filteredUsers.length, 'users') }}</span>
        <label>
          每页
          <select v-model.number="pagination.users.pageSize" @change="resetPage('users')">
            <option v-for="size in pageSizeOptions" :key="`users-${size}`" :value="size">{{ size }}</option>
          </select>
        </label>
        <button type="button" class="ghost-btn" :disabled="currentPage(filteredUsers.length, 'users') <= 1" @click="changePage('users', filteredUsers.length, -1)">
          上一页
        </button>
        <button type="button" class="ghost-btn" :disabled="currentPage(filteredUsers.length, 'users') >= pageCount(filteredUsers.length, 'users')" @click="changePage('users', filteredUsers.length, 1)">
          下一页
        </button>
      </div>
    </section>

    <div v-if="userModal.open" class="modal-backdrop" @click.self="closeUserModal">
      <section class="user-modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <p class="eyebrow">USER EDITOR</p>
            <h3>{{ userModal.mode === 'create' ? '新建用户' : '编辑用户' }}</h3>
          </div>
          <button type="button" class="modal-close" @click="closeUserModal">关闭</button>
        </div>

        <form class="user-modal-form" @submit.prevent="submitUserModal">
          <label>
            用户名
            <input
              v-model="userModal.form.username"
              :disabled="userModal.mode === 'edit'"
              placeholder="至少 3 位"
            />
          </label>

          <label>
            {{ userModal.mode === 'create' ? '初始密码' : '重置密码' }}
            <input
              v-model="userModal.form.password"
              type="password"
              :placeholder="userModal.mode === 'create' ? '至少 6 位' : '不填写则不修改密码'"
            />
          </label>

          <label>
            角色权限
            <select v-model="userModal.form.role">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </label>

          <label class="checkbox-label">
            <input v-model="userModal.form.active" type="checkbox" />
            启用账号
          </label>

          <div class="modal-actions">
            <button type="button" class="ghost-btn" @click="closeUserModal">取消</button>
            <button type="submit" :disabled="userSaving">
              {{ userSaving ? '保存中...' : userModal.mode === 'create' ? '创建用户' : '保存修改' }}
            </button>
          </div>
        </form>
      </section>
    </div>

    <section v-if="activeAdminSection === 'knowledge'" class="knowledge-manager">
      <div class="section-title">
        <div>
          <p class="eyebrow">KNOWLEDGE MANAGER</p>
          <h3>知识库管理</h3>
          <span class="section-help">
            疾病知识和药品说明支持导入、搜索、查看和删除；危险规则当前用于安全拦截，后台提供查看和搜索。
          </span>
        </div>

        <div class="tabs">
          <button type="button" :class="{ active: activeKnowledge === 'disease' }" @click="switchKnowledgeKind('disease')">
            疾病知识
          </button>
          <button type="button" :class="{ active: activeKnowledge === 'medicine' }" @click="switchKnowledgeKind('medicine')">
            药品说明
          </button>
          <button type="button" :class="{ active: activeKnowledge === 'warning' }" @click="switchKnowledgeKind('warning')">
            危险规则
          </button>
        </div>
      </div>

      <div class="knowledge-manager-grid">
        <article class="knowledge-tool-card">
          <div class="mini-heading">
            <strong>{{ activeKnowledgeLabel }}导入</strong>
            <span>{{ activeKnowledge === 'warning' ? '只读' : '支持 txt / json / md' }}</span>
          </div>

          <template v-if="activeKnowledge !== 'warning'">
            <input type="file" accept=".txt,.json,.md" @change="handleFile($event, activeKnowledge)" />
            <textarea v-model="uploads[activeKnowledge].content" :placeholder="activeKnowledgePlaceholder"></textarea>

            <button type="button" @click="uploadDoc(activeKnowledge)" :disabled="uploads[activeKnowledge].loading">
              {{ uploads[activeKnowledge].loading ? '上传中...' : `写入${activeKnowledgeLabel}` }}
            </button>
            <small v-if="uploads[activeKnowledge].message">{{ uploads[activeKnowledge].message }}</small>

            <div v-if="uploads[activeKnowledge].result" class="upload-result">
              <div class="upload-summary">
                <span>新增 {{ uploads[activeKnowledge].result.summary.created }}</span>
                <span>更新 {{ uploads[activeKnowledge].result.summary.updated }}</span>
                <span>疑似重复 {{ uploads[activeKnowledge].result.summary.similar }}</span>
              </div>

              <article v-for="item in uploads[activeKnowledge].result.data" :key="item.name" class="upload-row">
                <strong>{{ item.name }}</strong>
                <span :class="['upload-status', item.status]">
                  {{ item.status === 'created' ? '新增' : '更新已有' }}
                </span>
                <p v-if="item.duplicate_of">同名记录：{{ item.duplicate_of.name }}，本次已覆盖更新。</p>
                <p v-if="item.similar_duplicates?.length">
                  疑似重复：{{ item.similar_duplicates.map((dup) => dup.name).join('、') }}
                </p>
              </article>
            </div>
          </template>

          <p v-else class="empty-state">
            危险规则是安全拦截配置，当前版本只在后台统一查看和搜索，暂不开放导入写入。
          </p>
        </article>

        <article class="knowledge-tool-card">
          <div class="mini-heading">
            <strong>{{ activeKnowledgeLabel }}搜索 / 删除</strong>
            <span>{{ activeKnowledgeCount }} 条</span>
          </div>

          <form class="knowledge-search" @submit.prevent="searchKnowledgeManager">
            <input v-model="deleteTool.keyword" :placeholder="activeKnowledgeSearchPlaceholder" />
            <button type="submit" :disabled="deleteTool.loading">
              {{ deleteTool.loading ? '搜索中...' : '搜索' }}
            </button>
          </form>

          <p v-if="deleteTool.message" class="delete-message">{{ deleteTool.message }}</p>

          <div class="knowledge-list compact-list">
            <article v-for="item in pagedKnowledgeItems" :key="knowledgeKey(item)" class="knowledge-item">
              <template v-if="activeKnowledge === 'disease'">
                <strong>{{ item.name }}</strong>
                <span>{{ item.category || '未分类' }}</span>
                <p>{{ item.description || item.symptoms?.join('、') }}</p>
              </template>

              <template v-else-if="activeKnowledge === 'medicine'">
                <strong>{{ item.name }}</strong>
                <span>{{ item.type || '药品说明' }}</span>
                <p>{{ item.usage || item.notice || '暂无摘要' }}</p>
              </template>

              <template v-else>
                <strong>{{ item }}</strong>
                <span>危险规则</span>
                <p>命中后优先返回就医提醒。</p>
              </template>

              <button v-if="activeKnowledge !== 'warning'" type="button" class="delete-knowledge" @click="deleteKnowledgeItem(item)">
                删除
              </button>
            </article>
          </div>

          <div v-if="visibleKnowledgeManagerItems.length" class="pagination-bar">
            <span>{{ pageRangeLabel(visibleKnowledgeManagerItems.length, 'knowledge') }}</span>
            <label>
              每页
              <select v-model.number="pagination.knowledge.pageSize" @change="resetPage('knowledge')">
                <option v-for="size in pageSizeOptions" :key="`knowledge-${size}`" :value="size">{{ size }}</option>
              </select>
            </label>
            <button type="button" class="ghost-btn" :disabled="currentPage(visibleKnowledgeManagerItems.length, 'knowledge') <= 1" @click="changePage('knowledge', visibleKnowledgeManagerItems.length, -1)">
              上一页
            </button>
            <button type="button" class="ghost-btn" :disabled="currentPage(visibleKnowledgeManagerItems.length, 'knowledge') >= pageCount(visibleKnowledgeManagerItems.length, 'knowledge')" @click="changePage('knowledge', visibleKnowledgeManagerItems.length, 1)">
              下一页
            </button>
          </div>
        </article>
      </div>
    </section>

    <section v-if="activeAdminSection === 'system'" class="system-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">SYSTEM MAINTENANCE</p>
          <h3>系统维护</h3>
          <span class="section-help">
            这里集中放置后台刷新、向量索引更新和缓存同步操作，适合知识库更新后使用。
          </span>
        </div>
      </div>

      <div class="system-grid">
        <article>
          <strong>清除页面缓存</strong>
          <p>知识库或审核状态更新后，可清除管理页面缓存；进入具体分区时会重新加载对应数据。</p>
          <button type="button" @click="refreshAdminCaches">
            清除缓存
          </button>
        </article>

        <article>
          <strong>更新向量索引</strong>
          <p>知识库导入或删除后执行，让 RAG 检索结果同步到最新数据。</p>
          <button class="index-btn" type="button" @click="rebuildIndex" :disabled="indexLoading">
            {{ indexLoading ? '更新中...' : '更新向量索引' }}
          </button>
        </article>
      </div>

    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  apiUrl,
  clearPageCache,
  clearPageCacheByPrefix,
  readPageCache,
  writePageCache,
} from '../api'

const user = ref(null)
const loading = ref(false)
const indexLoading = ref(false)
const statusMessage = ref('')
const historyList = ref([])
const issueList = ref([])
const conversationSessions = ref([])
const agentRuns = ref([])
const users = ref([])
const userSaving = ref(false)
const userSearch = ref('')
const activeAdminSection = ref('review')
const activeKnowledge = ref('disease')
const activeReviewFilter = ref('pending')
const reviewUpdating = reactive({})
const reviewNotes = reactive({})
const reviewRetesting = reactive({})
const reviewRetestResults = reactive({})
const route = useRoute()
const pageSizeOptions = [5, 10, 20, 50]
const pagination = reactive({
  agent: { page: 1, pageSize: 10 },
  issues: { page: 1, pageSize: 10 },
  users: { page: 1, pageSize: 10 },
  knowledge: { page: 1, pageSize: 10 },
  history: { page: 1, pageSize: 10 },
})

const userModal = reactive({
  open: false,
  mode: 'create',
  originalUsername: '',
  form: {
    username: '',
    password: '',
    role: 'user',
    active: true,
  },
})

const adminSections = [
  { label: '回答复核', value: 'review' },
  { label: '知识库维护', value: 'knowledge' },
  { label: '用户管理', value: 'users' },
  { label: '系统维护', value: 'system' },
]

const reviewFilters = [
  { label: '待处理', value: 'pending' },
  { label: '已处理', value: 'processed' },
  { label: '已忽略', value: 'ignored' },
  { label: '全部', value: 'all' },
]

const reviewStatusLabels = {
  pending: '待处理',
  processed: '已处理',
  ignored: '已忽略',
}

const actionLabels = {
  danger_alert: '危险症状提醒',
  ask_followup: '追问关键信息',
  rag_answer: '症状知识库问答',
  medicine_query: '药品知识库查询',
  image_assist: '图片线索辅助分析',
  empty_input: '等待补充输入',
  agent_error: 'Agent 调度异常',
}

const intentLabels = {
  unknown: '未知输入',
  danger_alert: '疑似危险症状',
  followup: '信息不足需要追问',
  medicine_query: '药品用药咨询',
  image_assist: '图片相关健康咨询',
  symptom_query: '常见症状咨询',
  symptom_image: '症状图片咨询',
  general_health: '一般健康咨询',
}

const toolLabels = {
  normalize_input: '输入标准化',
  warning_check: '危险规则检查',
  rule_planner: '规则规划器',
  llm_planner: '大模型规划器',
  medicine_search: '药品库检索',
  rag_search: 'RAG 检索',
  llm_answer: '文本大模型生成',
  local_fallback: '本地兜底回答',
  agent_chat: 'Agent 接口',
}

const inputTypeLabels = {
  text: '文本',
  voice: '语音',
  image: '图片',
  video: '视频',
  mixed: '图文',
}

const labelAction = (action) => actionLabels[action] || action || '未判断'

const labelIntent = (intent) => intentLabels[intent] || intent || '未识别'

const labelTool = (tool) => toolLabels[tool] || tool || '未记录工具'

const labelInputType = (type) => inputTypeLabels[type] || type || '多模态输入'

const knowledge = ref({
  knowledge: {
    disease_count: 0,
    medicine_count: 0,
    warning_rule_count: 0,
    total_knowledge_count: 0,
  },
  diseases: [],
  medicines: [],
  warning_rules: [],
})

const uploads = reactive({
  disease: {
    fileName: '',
    content: '',
    loading: false,
    message: '',
    result: null,
  },
  medicine: {
    fileName: '',
    content: '',
    loading: false,
    message: '',
    result: null,
  },
})

const deleteTool = reactive({
  kind: 'medicine',
  keyword: '',
  loading: false,
  message: '',
  results: [],
})

const isAdmin = computed(() => user.value?.role === 'admin')

const pageCount = (total, name) => {
  const size = Math.max(1, Number(pagination[name]?.pageSize || 10))
  return Math.max(1, Math.ceil(total / size))
}

const currentPage = (total, name) => {
  const maxPage = pageCount(total, name)
  const page = Math.min(Math.max(1, Number(pagination[name]?.page || 1)), maxPage)
  if (pagination[name]) {
    pagination[name].page = page
  }
  return page
}

const pageItems = (items, name) => {
  const list = Array.isArray(items) ? items : []
  const page = currentPage(list.length, name)
  const size = Math.max(1, Number(pagination[name]?.pageSize || 10))
  const start = (page - 1) * size
  return list.slice(start, start + size)
}

const resetPage = (name) => {
  if (pagination[name]) {
    pagination[name].page = 1
  }
}

const changePage = (name, total, delta) => {
  if (!pagination[name]) return
  const next = currentPage(total, name) + delta
  pagination[name].page = Math.min(Math.max(1, next), pageCount(total, name))
}

const pageRangeLabel = (total, name) => {
  if (!total) return '暂无数据'
  const page = currentPage(total, name)
  const size = Math.max(1, Number(pagination[name]?.pageSize || 10))
  const start = (page - 1) * size + 1
  const end = Math.min(total, page * size)
  return `第 ${start}-${end} 条 / 共 ${total} 条`
}

const authHeaders = (extra = {}) => {
  const token = localStorage.getItem('ragToken') || ''

  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  }
}

const clearStaleAdminSession = () => {
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  user.value = null
  window.dispatchEvent(new Event('rag-user-change'))
}

const parseAdminResponse = async (response) => {
  if (response.status === 401 || response.status === 403) {
    statusMessage.value = '管理员登录已失效或权限不足，请重新登录管理员账号。'
    clearStaleAdminSession()
    const error = new Error('admin forbidden')
    error.expectedAuthFailure = true
    throw error
  }

  return response.json()
}

const adminCachePrefix = () => `admin:${user.value?.id || user.value?.username || 'guest'}:`

const adminCacheKey = (name) => `${adminCachePrefix()}${name}`

const cachedAdminGet = async (name, path, force = false) => {
  const key = adminCacheKey(name)
  const cached = force ? null : readPageCache(key)

  if (cached) {
    return cached
  }

  const response = await fetch(apiUrl(path), {
    headers: authHeaders(),
  })
  const data = await parseAdminResponse(response)
  return writePageCache(key, data)
}

const clearAdminDataCache = () => {
  clearPageCacheByPrefix(adminCachePrefix())
  clearPageCacheByPrefix('knowledge:')
  clearPageCache('home:stats')
  clearPageCache('analytics:summary')
}

const refreshAdminCaches = () => {
  clearAdminDataCache()
  statusMessage.value = '管理页面缓存已清除，进入具体分区时会重新加载。'
}

const visibleKnowledge = computed(() => {
  if (activeKnowledge.value === 'disease') {
    return knowledge.value.diseases
  }

  if (activeKnowledge.value === 'medicine') {
    return knowledge.value.medicines
  }

  return knowledge.value.warning_rules
})

const activeKnowledgeLabel = computed(() => {
  if (activeKnowledge.value === 'disease') return '疾病知识'
  if (activeKnowledge.value === 'medicine') return '药品说明'
  return '危险规则'
})

const activeKnowledgeCount = computed(() => visibleKnowledge.value.length)

const activeKnowledgePlaceholder = computed(() => {
  if (activeKnowledge.value === 'medicine') {
    return '可粘贴药品说明书 JSON 或纯文本，例如：适应症、注意事项、禁忌、不良反应。'
  }

  return '可粘贴疾病知识 JSON 或纯文本，例如：疾病名称、症状、护理建议、用药注意、就医提醒。'
})

const activeKnowledgeSearchPlaceholder = computed(() => {
  if (activeKnowledge.value === 'warning') return '搜索危险症状规则关键词'
  if (activeKnowledge.value === 'medicine') return '输入药品名称、类型、适用情况或注意事项'
  return '输入疾病名称、症状、分类或护理建议'
})

const visibleKnowledgeManagerItems = computed(() => {
  if (deleteTool.results.length) return deleteTool.results

  const keyword = deleteTool.keyword.trim().toLowerCase()
  const source = visibleKnowledge.value
  if (!keyword) return source

  return source.filter((item) => {
    if (typeof item === 'string') {
      return item.toLowerCase().includes(keyword)
    }

    return JSON.stringify(item).toLowerCase().includes(keyword)
  })
})

const pagedKnowledgeItems = computed(() => pageItems(visibleKnowledgeManagerItems.value, 'knowledge'))

const normalizedReviewStatus = (item) => item.review_status || (item.needs_review ? 'pending' : 'processed')

const filteredIssues = computed(() => {
  const list = issueList.value

  if (['pending', 'processed', 'ignored'].includes(activeReviewFilter.value)) {
    return list.filter((item) => normalizedReviewStatus(item) === activeReviewFilter.value)
  }

  return list
})

const pagedIssues = computed(() => pageItems(filteredIssues.value, 'issues'))

const issueStatusCount = (status) => issueList.value.filter((item) => normalizedReviewStatus(item) === status).length

const reviewStatusLabel = (status) => reviewStatusLabels[status || 'pending'] || '待处理'

const reviewFilterLabel = (value) => {
  return reviewFilters.find((item) => item.value === value)?.label || '全部'
}

const labelRetestContext = (context = {}) => {
  const count = Number(context.used_count || 0)
  if (context.source === 'session' && count > 0) {
    return `带上下文 ${count} 条`
  }
  if (context.source === 'fallback_topic' && count > 0) {
    return '仅继承药品主题'
  }
  return '未找到上下文，单句复测'
}

const currentReviewRetest = (item) => {
  const retest = reviewRetestResults[item.record_id] || item.review_retest
  if (!retest || typeof retest !== 'object') return null
  if (!retest.current || typeof retest.current !== 'object') return null
  if (!retest.previous || typeof retest.previous !== 'object') return null
  return retest
}

const setReviewFilter = (value) => {
  activeReviewFilter.value = value
  resetPage('issues')
}

const isReviewUpdating = (item, status = '') => {
  const current = reviewUpdating[item.record_id]
  return status ? current === status : Boolean(current)
}

const isReviewRetesting = (item) => Boolean(reviewRetesting[item.record_id])

const roleLabel = (role) => (role === 'admin' ? '管理员' : '普通用户')

const filteredUsers = computed(() => {
  const keyword = userSearch.value.trim().toLowerCase()
  if (!keyword) return users.value

  return users.value.filter((item) => {
    const username = String(item.username || '').toLowerCase()
    const role = roleLabel(item.role).toLowerCase()
    const active = item.active === false ? '停用 已停用 disabled' : '启用 启用中 active'
    return `${username} ${role} ${active}`.includes(keyword)
  })
})

const pagedUsers = computed(() => pageItems(filteredUsers.value, 'users'))

const pagedHistory = computed(() => pageItems(historyList.value, 'history'))

const lowConfidenceRuns = computed(() => {
  return agentRuns.value.filter((item) => item.flags?.low_confidence || Number(item.confidence || 0) < 0.6)
})

const noRetrievalRuns = computed(() => {
  return agentRuns.value.filter((item) => item.flags?.no_retrieval)
})

const visualRuns = computed(() => {
  return agentRuns.value.filter((item) => item.flags?.used_image)
})

const llmRuns = computed(() => {
  return agentRuns.value.filter((item) => item.flags?.used_llm || item.llm_used)
})

const pagedAgentRuns = computed(() => pageItems(agentRuns.value, 'agent'))

const formatPercent = (value) => {
  const number = Number(value || 0)
  if (!Number.isFinite(number)) return '0%'
  return `${Math.round(number * 100)}%`
}

const compactText = (text, maxLength = 72) => {
  const value = String(text || '').replace(/\s+/g, ' ').trim()
  if (!value) return '未记录输入摘要'
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
}

const formatTools = (tools = []) => {
  return (tools || []).map((tool) => labelTool(tool)).filter(Boolean).join('、')
}

const knowledgeKey = (item) => {
  if (typeof item === 'string') {
    return item
  }

  return `${item.name}-${item.type || item.category || ''}`
}

const loadUser = () => {
  const raw = localStorage.getItem('ragUser')
  user.value = raw ? JSON.parse(raw) : null
}

const loadAdminData = async (force = false) => {
  if (!isAdmin.value) {
    return
  }

  loading.value = true
  statusMessage.value = ''

  try {
    if (activeAdminSection.value === 'review') {
      const data = await cachedAdminGet('issues', '/api/admin/review/issues', force)
      issueList.value = data.data || []
    } else if (activeAdminSection.value === 'knowledge') {
      knowledge.value = await cachedAdminGet('knowledge', '/api/admin/knowledge', force)
    } else if (activeAdminSection.value === 'users') {
      const data = await cachedAdminGet('users', '/api/admin/users', force)
      users.value = data.data || []
    }
  } catch (error) {
    if (!error.expectedAuthFailure) {
      console.error(error)
    }
    if (!statusMessage.value) {
      statusMessage.value = '后台数据加载失败，请检查后端服务是否正常运行。'
    }
  } finally {
    loading.value = false
  }
}

const selectAdminSection = async (section) => {
  activeAdminSection.value = section
  await loadAdminData()
}

const resetUserModalForm = () => {
  userModal.form.username = ''
  userModal.form.password = ''
  userModal.form.role = 'user'
  userModal.form.active = true
}

const openCreateUserModal = () => {
  userModal.mode = 'create'
  userModal.originalUsername = ''
  resetUserModalForm()
  userModal.open = true
}

const openEditUserModal = (item) => {
  userModal.mode = 'edit'
  userModal.originalUsername = item.username
  userModal.form.username = item.username
  userModal.form.password = ''
  userModal.form.role = item.role || 'user'
  userModal.form.active = item.active !== false
  userModal.open = true
}

const closeUserModal = () => {
  if (userSaving.value) return
  userModal.open = false
}

const createSystemUser = async (form) => {
  userSaving.value = true
  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl('/api/admin/users'), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(form),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message

    if (data.success) {
      closeUserModal()
      clearAdminDataCache()
      await loadAdminData(true)
    }
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '用户创建失败。'
    }
  } finally {
    userSaving.value = false
  }
}

const updateSystemUser = async (username, form) => {
  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl(`/api/admin/users/${encodeURIComponent(username)}`), {
      method: 'PUT',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        role: form.role,
        active: form.active,
        password: form.password,
      }),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message

    if (data.success) {
      closeUserModal()
      clearAdminDataCache()
      await loadAdminData(true)
    }
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '用户更新失败。'
    }
  }
}

const submitUserModal = async () => {
  const form = {
    username: userModal.form.username.trim(),
    password: userModal.form.password,
    role: userModal.form.role,
    active: userModal.form.active,
  }

  if (userModal.mode === 'create') {
    await createSystemUser(form)
    return
  }

  await updateSystemUser(userModal.originalUsername, form)
}

const deleteSystemUser = async (username) => {
  if (!confirm(`确定删除用户 ${username} 吗？此操作会移除该账号，建议确认不是正在使用的成员账号。`)) {
    return
  }

  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl(`/api/admin/users/${encodeURIComponent(username)}`), {
      method: 'DELETE',
      headers: authHeaders(),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message
    clearAdminDataCache()
    await loadAdminData(true)
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '用户删除失败。'
    }
  }
}

const handleFile = (event, kind) => {
  const file = event.target.files?.[0]

  if (!file) {
    return
  }

  uploads[kind].fileName = file.name
  uploads[kind].message = `已选择：${file.name}`
  uploads[kind].result = null

  const reader = new FileReader()
  reader.onload = () => {
    uploads[kind].content = String(reader.result || '')
  }
  reader.readAsText(file, 'utf-8')
}

const issueTagClass = (type) => {
  if (type === '药品库缺失') return 'medicine'
  if (type === '图片识别待复核') return 'image'
  if (type === 'RAG低命中') return 'rag'
  return 'neutral'
}

const switchKnowledgeKind = (kind) => {
  activeKnowledge.value = kind
  deleteTool.kind = kind === 'warning' ? 'disease' : kind
  deleteTool.keyword = ''
  deleteTool.message = ''
  deleteTool.results = []
  resetPage('knowledge')
}

const loadReviewIssues = async () => {
  statusMessage.value = '正在刷新复核样本...'

  try {
    const data = await cachedAdminGet('issues', '/api/admin/review/issues', true)
    issueList.value = data.data || []
    statusMessage.value = '复核样本已刷新。'
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '复核样本刷新失败。'
    }
  }
}

const retestReviewTicket = async (item) => {
  const recordId = item.record_id
  reviewRetesting[recordId] = true
  statusMessage.value = '正在使用当前系统重新测试原问题...'

  try {
    const response = await fetch(apiUrl(`/api/admin/review/issues/${recordId}/retest`), {
      method: 'POST',
      headers: authHeaders(),
    })
    const data = await parseAdminResponse(response)
    if (!data.success) {
      statusMessage.value = data.message || '重新测试失败。'
      return
    }

    reviewRetestResults[recordId] = data.data
    delete reviewRetesting[recordId]
    clearPageCache(adminCacheKey('issues'))
    clearPageCache('analytics:summary')
    await loadReviewIssues()
    statusMessage.value = '重新测试完成，最新结果已保存。'
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '重新测试失败，请检查后端服务是否正常运行。'
    }
  } finally {
    delete reviewRetesting[recordId]
  }
}

const updateReviewTicket = async (item, status) => {
  const note = String(reviewNotes[item.record_id] || '').trim()
  if (!note) {
    statusMessage.value = '请先填写处理说明。'
    return
  }
  const originalStatus = item.review_status
  const originalNote = item.review_note
  const originalNeedsReview = item.needs_review

  reviewUpdating[item.record_id] = status
  item.review_status = status
  item.review_note = note
  item.needs_review = false
  statusMessage.value = status === 'processed'
    ? '样本已标记为已处理。'
    : '样本已忽略。'

  try {
    const response = await fetch(apiUrl(`/api/admin/review/issues/${item.record_id}/status`), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        status,
        note,
      }),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message

    if (data.success) {
      const updated = data.data || {}
      issueList.value = issueList.value.map((issue) => {
        if (issue.record_id !== item.record_id) return issue

        return {
          ...issue,
          review_status: updated.review_status || status,
          review_note: updated.review_note || note,
          review_time: updated.review_time || issue.review_time,
          needs_review: false,
        }
      })
      clearPageCache(adminCacheKey('issues'))
      clearPageCache(adminCacheKey('history'))
      clearPageCache('analytics:summary')
      await loadReviewIssues()
    }
  } catch (error) {
    console.error(error)
    item.review_status = originalStatus
    item.review_note = originalNote
    item.needs_review = originalNeedsReview
    if (!statusMessage.value) {
      statusMessage.value = '样本状态更新失败，请检查后端服务是否正常运行。'
    }
  } finally {
    delete reviewUpdating[item.record_id]
  }
}

const uploadDoc = async (kind) => {
  const target = uploads[kind]

  if (!target.content.trim()) {
    target.message = '请先选择文件或粘贴文档内容。'
    return
  }

  target.loading = true
  target.message = ''
  target.result = null

  try {
    const response = await fetch(apiUrl(`/api/admin/upload/${kind}`), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        file_name: target.fileName || `${kind}-manual-input.txt`,
        content: target.content,
      }),
    })

    const data = await parseAdminResponse(response)
    target.message = data.message
    target.result = data.success
      ? {
          summary: data.summary || { created: 0, updated: 0, similar: 0 },
          data: data.data || [],
        }
      : null

    if (data.success) {
      target.content = ''
      target.fileName = ''
      clearAdminDataCache()
      await loadAdminData(true)
    }
  } catch (error) {
    console.error(error)
    target.message = '上传失败，请检查后端服务是否正常运行。'
  } finally {
    target.loading = false
  }
}

const searchDeleteCandidates = async () => {
  if (!deleteTool.keyword.trim()) {
    deleteTool.message = '请输入要搜索的关键词。'
    deleteTool.results = []
    resetPage('knowledge')
    return
  }

  deleteTool.loading = true
  deleteTool.message = ''
  deleteTool.results = []

  try {
    const response = await fetch(apiUrl('/api/admin/knowledge/search'), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        kind: deleteTool.kind,
        keyword: deleteTool.keyword,
      }),
    })

    const data = await parseAdminResponse(response)
    deleteTool.message = data.message
    deleteTool.results = data.data || []
    resetPage('knowledge')
  } catch (error) {
    console.error(error)
    deleteTool.message = '搜索失败，请检查后端服务是否正常运行。'
  } finally {
    deleteTool.loading = false
  }
}

const searchKnowledgeManager = async () => {
  if (activeKnowledge.value === 'warning') {
    deleteTool.results = []
    deleteTool.message = deleteTool.keyword.trim()
      ? '已在危险规则中按关键词筛选。'
      : '已显示全部危险规则。'
    resetPage('knowledge')
    return
  }

  deleteTool.kind = activeKnowledge.value
  await searchDeleteCandidates()
}

const deleteKnowledgeItem = async (item) => {
  const kind = activeKnowledge.value === 'warning' ? deleteTool.kind : activeKnowledge.value
  const kindLabel = kind === 'disease' ? '疾病知识' : '药品说明'

  if (!confirm(`确定删除${kindLabel}“${item.name}”吗？删除后需要更新向量索引。`)) {
    return
  }

  deleteTool.loading = true
  deleteTool.message = ''

  try {
    const response = await fetch(apiUrl(`/api/admin/knowledge/${kind}/${item.id}`), {
      method: 'DELETE',
      headers: authHeaders(),
    })

    const data = await parseAdminResponse(response)
    deleteTool.message = data.message

    if (data.success) {
      deleteTool.results = deleteTool.results.filter((candidate) => candidate.id !== item.id)
      if (kind === 'disease') {
        knowledge.value.diseases = knowledge.value.diseases.filter((candidate) => candidate.id !== item.id)
      } else {
        knowledge.value.medicines = knowledge.value.medicines.filter((candidate) => candidate.id !== item.id)
      }
      statusMessage.value = '知识已删除。请点击“更新向量索引”，同步 RAG 检索结果。'
      clearAdminDataCache()
    }
  } catch (error) {
    console.error(error)
    deleteTool.message = '删除失败，请检查后端服务是否正常运行。'
  } finally {
    deleteTool.loading = false
  }
}

const rebuildIndex = async () => {
  indexLoading.value = true
  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl('/api/admin/vector/rebuild'), {
      method: 'POST',
      headers: authHeaders(),
    })
    const data = await parseAdminResponse(response)
    const indexData = data.data || {}
    const modeLabel = indexData.index_mode === 'semantic' ? '语义向量检索' : '关键词检索'
    const modelText = indexData.embedding_model ? `，模型：${indexData.embedding_model}` : ''
    const fallbackText = indexData.fallback ? `，${indexData.fallback_reason}` : ''
    statusMessage.value = `${data.message}，模式：${modeLabel}${modelText}，文档数：${indexData.doc_count}，向量维度：${indexData.dimension}${fallbackText}`
  } catch (error) {
    console.error(error)
    statusMessage.value = '向量索引更新失败，请检查后端服务是否正常运行。'
  } finally {
    indexLoading.value = false
  }
}

onMounted(async () => {
  const requestedSection = String(route.query.section || '')
  if (adminSections.some((section) => section.value === requestedSection)) {
    activeAdminSection.value = requestedSection
  }
  loadUser()
  await loadAdminData()
})

watch(userSearch, () => resetPage('users'))
watch(() => deleteTool.keyword, () => resetPage('knowledge'))
watch(activeReviewFilter, () => resetPage('issues'))
</script>

<style scoped>
.admin-page {
  display: grid;
  gap: 24px;
}

.access-gate,
.admin-hero,
.agent-log-panel,
.review-workbench,
.user-panel,
.knowledge-manager,
.delete-panel,
.knowledge-tool-card,
.upload-card,
.knowledge-panel,
.history-panel {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.access-gate {
  display: grid;
  gap: 12px;
  max-width: 720px;
  padding: 36px;
}

.access-gate h2,
.admin-hero h2 {
  color: var(--text-primary);
  font-size: clamp(30px, 5vw, 46px);
  font-weight: 900;
  line-height: 1.15;
}

.access-gate p,
.admin-hero p,
.knowledge-tool-card p,
.upload-card p {
  color: var(--text-secondary);
  line-height: 1.85;
}

.access-gate a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: max-content;
  min-height: 42px;
  padding: 0 18px;
  color: #ffffff;
  text-decoration: none;
  background: var(--medical-blue);
  border-radius: 8px;
  font-weight: 900;
}

.eyebrow {
  margin-bottom: 8px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.admin-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: clamp(24px, 4vw, 40px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.88)),
    #ffffff;
}

.admin-hero p {
  max-width: 720px;
  margin-top: 12px;
}

.admin-actions,
.tabs,
.mark-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

button {
  min-height: 42px;
  padding: 0 16px;
  color: #ffffff;
  background: var(--medical-blue);
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
  transition: transform 0.16s ease, opacity 0.16s ease, background 0.16s ease, border-color 0.16s ease;
}

button:not(:disabled):active {
  transform: translateY(1px);
}

button:disabled {
  opacity: 0.72;
  background: #94a3b8;
  cursor: not-allowed;
}

.index-btn {
  background: var(--pharmacy-teal);
}

.overview-dashboard {
  display: grid;
  gap: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
}

.metric-grid article {
  min-height: 108px;
  padding: 20px;
  text-align: center;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.metric-grid strong {
  display: block;
  color: var(--medical-blue);
  font-size: 31px;
  font-weight: 900;
  line-height: 1.15;
}

.metric-grid span {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-weight: 800;
}

.overview-insights {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.overview-insights article {
  display: grid;
  gap: 10px;
  min-height: 132px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.overview-insights article > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.overview-insights span {
  color: var(--text-muted);
  font-weight: 900;
}

.overview-insights strong {
  color: var(--pharmacy-teal);
  font-size: 30px;
  font-weight: 900;
  line-height: 1.1;
}

.overview-insights p {
  color: var(--text-secondary);
  line-height: 1.75;
}

.status-message {
  padding: 13px 16px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-weight: 800;
}

.admin-section-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.admin-section-tabs button {
  min-height: 38px;
  color: var(--text-secondary);
  background: #f8fbfd;
  border: 1px solid var(--border);
}

.admin-section-tabs button.active {
  color: #ffffff;
  background: var(--medical-blue);
  border-color: var(--medical-blue);
}

.agent-log-panel {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.agent-observe-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.agent-observe-summary article {
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.agent-observe-summary strong,
.agent-observe-summary span {
  display: block;
}

.agent-observe-summary strong {
  color: var(--medical-blue);
  font-size: 28px;
  font-weight: 900;
  line-height: 1.1;
}

.agent-observe-summary span {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 900;
}

.agent-log-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.agent-log-grid > article {
  display: grid;
  gap: 12px;
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.mini-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.mini-heading strong {
  color: var(--text-primary);
  font-weight: 900;
}

.mini-heading span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 900;
}

.mini-list {
  display: grid;
  gap: 8px;
}

.mini-row {
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.mini-row strong,
.mini-row span {
  display: block;
}

.mini-row strong {
  color: var(--text-primary);
  font-weight: 900;
}

.mini-row span {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.agent-run-table {
  display: grid;
  gap: 10px;
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.agent-run-detail {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.agent-run-detail summary {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(280px, 1.2fr);
  gap: 14px;
  align-items: center;
  padding: 14px;
  cursor: pointer;
  list-style: none;
}

.agent-run-detail summary::-webkit-details-marker {
  display: none;
}

.agent-run-detail summary strong,
.agent-run-detail summary span {
  display: block;
}

.agent-run-detail summary strong {
  color: var(--text-primary);
  font-weight: 900;
}

.agent-run-detail summary > div:first-child span {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.agent-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.agent-chip {
  padding: 4px 8px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.agent-chip.ok {
  color: #166534;
  background: #f0fdf4;
}

.agent-chip.warn {
  color: #92400e;
  background: #fffbeb;
}

.agent-chip.muted {
  color: #64748b;
  background: #f1f5f9;
}

.agent-detail-body {
  display: grid;
  gap: 12px;
  padding: 0 14px 14px;
}

.agent-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.agent-detail-grid div {
  padding: 12px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.agent-detail-grid span,
.agent-detail-grid strong {
  display: block;
}

.agent-detail-grid span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 900;
}

.agent-detail-grid strong {
  margin-top: 5px;
  color: var(--text-primary);
  font-weight: 900;
  line-height: 1.55;
}

.agent-step-list {
  display: grid;
  gap: 8px;
}

.agent-step-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.agent-step-list b {
  color: var(--text-primary);
  font-weight: 900;
}

.agent-step-list span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 900;
}

.agent-reason {
  padding: 12px;
  color: var(--text-secondary);
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  line-height: 1.7;
  font-weight: 800;
}

.pagination-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 12px;
}

.pagination-bar span,
.pagination-bar label {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 900;
}

.pagination-bar label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.pagination-bar select {
  width: auto;
  min-width: 76px;
  min-height: 38px;
  padding: 0 10px;
  color: var(--text-primary);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-weight: 900;
}

.review-workbench {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.review-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.review-summary article {
  padding: 14px 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.review-summary strong,
.review-summary span {
  display: block;
}

.review-summary strong {
  color: var(--medical-blue);
  font-size: 26px;
  font-weight: 900;
  line-height: 1.15;
}

.review-summary span {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 900;
}

.review-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.review-toolbar span {
  color: var(--text-secondary);
  font-weight: 900;
}

.issue-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.issue-card {
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.issue-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.issue-title-block {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.issue-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.issue-head strong {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.issue-head small {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-weight: 800;
}

.issue-tag {
  width: max-content;
  padding: 4px 9px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.issue-tag.medicine {
  color: #92400e;
  background: #fffbeb;
}

.issue-tag.rag {
  color: #075985;
  background: #eff6ff;
}

.issue-tag.image {
  color: #166534;
  background: #f0fdf4;
}

.issue-tag.bad {
  color: #991b1b;
  background: #fef2f2;
}

.ticket-status {
  width: max-content;
  padding: 4px 9px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.ticket-status.pending {
  color: #075985;
  background: #eff6ff;
}

.ticket-status.processed {
  color: #166534;
  background: #f0fdf4;
}

.ticket-status.ignored {
  color: #64748b;
  background: #f1f5f9;
}

.issue-section {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.issue-section-title {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.issue-question,
.issue-fix {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.issue-answer {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.issue-answer summary {
  padding: 10px 12px;
  color: var(--medical-blue);
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
}

.issue-answer pre {
  max-height: 260px;
  margin: 0;
  padding: 0 12px 12px;
  overflow: auto;
  color: var(--text-secondary);
  white-space: pre-wrap;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  line-height: 1.7;
}

.retest-result {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-left: 4px solid var(--pharmacy-teal);
  border-radius: 8px;
}

.retest-result .mini-heading {
  padding-bottom: 8px;
  border-bottom: 1px solid #e4edf3;
}

.retest-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.retest-metrics span,
.retest-result p {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 800;
}

.retest-result pre {
  max-height: 300px;
  margin: 0;
  padding: 10px 12px;
  overflow: auto;
  color: var(--text-primary);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  white-space: pre-wrap;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  line-height: 1.7;
}

.review-note-input {
  width: 100%;
  min-height: 64px;
  margin: 0;
  resize: vertical;
}

.issue-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.issue-meta span {
  padding: 4px 8px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.issue-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.issue-actions button {
  min-width: 108px;
}

.retest-btn {
  background: var(--pharmacy-teal);
}

.issue-notes {
  display: grid;
  gap: 8px;
}

.issue-notes .feedback-note {
  margin-top: 0;
  background: #ffffff;
  border-color: var(--border);
}

.ghost-btn {
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
}

.invalid-btn {
  color: #991b1b;
  background: #fff7f7;
  border: 1px solid #fecaca;
}

.knowledge-manager {
  display: grid;
  gap: 18px;
  padding: 22px;
}

.system-panel {
  display: grid;
  gap: 18px;
  padding: 22px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.system-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.system-grid article {
  display: grid;
  align-content: start;
  gap: 12px;
  padding: 18px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.system-grid strong {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.system-grid p {
  color: var(--text-secondary);
  line-height: 1.7;
}

.knowledge-manager-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.85fr) minmax(360px, 1.15fr);
  gap: 18px;
}

.knowledge-tool-card {
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 18px;
  background: #ffffff;
}

.knowledge-tool-card textarea {
  min-height: 220px;
}

.knowledge-search {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto;
  gap: 12px;
}

.compact-list {
  max-height: 560px;
}

.compact-list .knowledge-item {
  position: relative;
  padding-right: 108px;
}

.compact-list .delete-knowledge {
  position: absolute;
  top: 14px;
  right: 14px;
  min-height: 34px;
  padding: 0 12px;
}

.upload-grid,
.admin-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
}

.delete-panel {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.delete-search {
  display: grid;
  grid-template-columns: 160px minmax(220px, 1fr) auto;
  gap: 12px;
}

.delete-message {
  padding: 10px 12px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-weight: 800;
}

.delete-list {
  display: grid;
  gap: 10px;
}

.delete-card {
  display: grid;
  grid-template-columns: minmax(180px, 0.7fr) minmax(240px, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 14px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.delete-card strong,
.delete-card span {
  display: block;
}

.delete-card strong {
  color: var(--text-primary);
  font-weight: 900;
}

.delete-card span {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.delete-card p {
  max-height: 72px;
  overflow: auto;
  color: var(--text-secondary);
  line-height: 1.65;
}

.delete-knowledge {
  background: var(--danger);
}

.user-panel {
  display: grid;
  gap: 18px;
  padding: 22px;
}

.user-toolbar {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto;
  gap: 12px;
  align-items: end;
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.user-search,
.checkbox-label {
  display: grid;
  gap: 7px;
  color: var(--text-primary);
  font-weight: 900;
}

.checkbox-label {
  display: flex;
  align-items: center;
  min-height: 42px;
  color: var(--text-secondary);
}

.checkbox-label input {
  width: 16px;
  min-height: 16px;
}

.checkbox-label.compact {
  justify-content: center;
}

.user-table {
  display: grid;
  gap: 10px;
}

.compact-table {
  gap: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.user-table-head,
.user-row {
  display: grid;
  grid-template-columns: minmax(150px, 1.1fr) 120px 110px minmax(160px, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
}

.user-table-head {
  color: var(--text-muted);
  background: #f8fbfd;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  font-weight: 900;
}

.user-row {
  background: #ffffff;
  border-bottom: 1px solid var(--border);
}

.user-row:last-child {
  border-bottom: 0;
}

.user-row strong {
  color: var(--text-primary);
  font-weight: 900;
}

.user-row span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 800;
}

.user-state {
  width: max-content;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.user-state.enabled {
  color: #166534;
  background: #f0fdf4;
}

.user-state.disabled {
  color: #991b1b;
  background: #fef2f2;
}

.user-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.delete-user {
  background: var(--danger);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.42);
}

.user-modal {
  display: grid;
  gap: 18px;
  width: min(560px, 100%);
  padding: 24px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.modal-head h3 {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 900;
}

.modal-close {
  min-height: 36px;
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
}

.user-modal-form {
  display: grid;
  gap: 14px;
}

.user-modal-form label {
  display: grid;
  gap: 7px;
  color: var(--text-primary);
  font-weight: 900;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.upload-card {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.card-heading,
.section-title,
.review-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.card-heading {
  align-items: flex-start;
}

.card-heading > span {
  display: grid;
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  place-items: center;
  color: #ffffff;
  background: var(--medicine-amber);
  border-radius: 8px;
  font-weight: 900;
}

.upload-card h3,
.section-title h3 {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 900;
}

.section-help {
  display: block;
  max-width: 620px;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
  font-weight: 700;
}

input,
select,
textarea {
  width: 100%;
  color: var(--text-primary);
  background: #f8fbfd;
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
}

input {
  min-height: 42px;
  padding: 9px 12px;
}

select {
  min-height: 42px;
  padding: 9px 12px;
}

textarea {
  min-height: 180px;
  padding: 14px;
  resize: vertical;
  line-height: 1.75;
}

input:focus,
select:focus,
textarea:focus {
  background: #ffffff;
  border-color: var(--medical-blue);
}

.checkbox-label input {
  width: 16px;
  min-height: 16px;
  accent-color: var(--medical-blue);
}

.upload-card small {
  color: var(--pharmacy-teal);
  font-weight: 800;
}

.upload-result {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.upload-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.upload-summary span {
  padding: 4px 8px;
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.upload-row {
  display: grid;
  gap: 7px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.upload-row strong {
  color: var(--text-primary);
  font-weight: 900;
}

.upload-row p {
  color: var(--text-secondary);
  line-height: 1.65;
}

.upload-status {
  width: max-content;
  padding: 3px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.upload-status.created {
  color: #166534;
  background: #f0fdf4;
}

.upload-status.updated {
  color: #92400e;
  background: #fffbeb;
}

.knowledge-panel,
.history-panel {
  min-height: 520px;
  padding: 22px;
}

.section-title {
  align-items: center;
  margin-bottom: 16px;
}

.tabs button {
  min-height: 36px;
  color: var(--text-secondary);
  background: #f8fbfd;
  border: 1px solid var(--border);
}

.tabs button.active {
  color: #ffffff;
  background: var(--medical-blue);
}

.knowledge-list,
.review-list {
  display: grid;
  gap: 12px;
  max-height: 640px;
  overflow: auto;
  padding-right: 4px;
}

.knowledge-item,
.review-card,
.empty-state {
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.knowledge-item strong {
  display: block;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 900;
}

.knowledge-item span {
  display: inline-flex;
  margin-top: 6px;
  padding: 3px 8px;
  color: var(--medical-blue);
  background: #eff6ff;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.knowledge-item p,
.empty-state {
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.review-card {
  background: #ffffff;
}

.review-header {
  align-items: flex-start;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.review-header strong {
  color: var(--text-primary);
  font-weight: 900;
}

.review-header span {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

pre {
  max-height: 160px;
  margin-top: 12px;
  overflow: auto;
  color: var(--text-secondary);
  white-space: pre-wrap;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  line-height: 1.75;
}

.review-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.review-meta span {
  padding: 4px 8px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.review-meta .danger-tag,
.review-meta .error-tag {
  color: #991b1b;
  background: #fef2f2;
}

.feedback-note {
  margin-top: 10px;
  padding: 10px 12px;
  color: var(--text-secondary);
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
  line-height: 1.7;
}

.mark-row {
  margin-top: 12px;
}

.mark-row input {
  flex: 1 1 260px;
}

.mark-row button {
  background: var(--danger);
}

@media (max-width: 980px) {
  .admin-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .overview-insights {
    grid-template-columns: repeat(2, 1fr);
  }

  .user-toolbar,
  .user-row,
  .user-table-head,
  .delete-search,
  .delete-card {
    grid-template-columns: 1fr;
  }

  .review-summary,
  .agent-observe-summary,
  .issue-list,
  .agent-log-grid {
    grid-template-columns: 1fr;
  }

  .agent-run-detail summary,
  .agent-detail-grid {
    grid-template-columns: 1fr;
  }

  .checkbox-label.compact {
    justify-content: flex-start;
  }

  .user-actions,
  .modal-actions {
    justify-content: flex-start;
  }

  .upload-grid,
  .knowledge-manager-grid,
  .knowledge-search,
  .system-grid,
  .admin-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .overview-insights {
    grid-template-columns: 1fr;
  }

  .section-title,
  .review-header,
  .review-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
