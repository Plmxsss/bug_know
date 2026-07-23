<script setup lang="ts">
import { ref } from 'vue'
import {
  askKnowledgeQuestion,
  type KnowledgeQuestionAnswer,
} from '../api/questions'
import { apiErrorMessage } from '../api/http'

const props = defineProps<{
  taskId: number
}>()

const question = ref('')
const answer = ref<KnowledgeQuestionAnswer | null>(null)
const loading = ref(false)
const errorMessage = ref('')

async function submitQuestion(): Promise<void> {
  const cleanQuestion = question.value.trim()
  if (cleanQuestion.length < 2) {
    errorMessage.value = '请输入至少两个字符的问题。'
    return
  }

  loading.value = true
  answer.value = null
  errorMessage.value = ''
  try {
    answer.value = await askKnowledgeQuestion(props.taskId, cleanQuestion)
  } catch (error) {
    errorMessage.value = apiErrorMessage(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="question-panel">
    <div>
      <p class="panel-label">BOUNDED LANGCHAIN AGENT</p>
      <h2>继续追问</h2>
      <p>
        Agent 只能检索本次任务识别出的害虫，最终回答会再次校验引用。
      </p>
    </div>

    <form @submit.prevent="submitQuestion">
      <textarea
        v-model="question"
        maxlength="500"
        rows="3"
        placeholder="例如：这种害虫在什么条件下容易发生？"
      ></textarea>
      <button type="submit" :disabled="loading">
        {{ loading ? 'Agent 正在检索…' : '提交问题' }}
      </button>
    </form>

    <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

    <article v-if="answer" class="question-answer">
      <div class="agent-trace">
        <span>Agent 实际检索词</span>
        <code v-for="query in answer.planned_queries" :key="query">
          {{ query }}
        </code>
      </div>
      <h3>回答</h3>
      <p>{{ answer.answer }}</p>
      <h4>不确定性</h4>
      <p>{{ answer.uncertainty }}</p>

      <div class="question-references">
        <h4>本次引用</h4>
        <ul>
          <li v-for="reference in answer.references" :key="reference.point_id">
            <a
              v-if="reference.source_url"
              :href="reference.source_url"
              target="_blank"
              rel="noreferrer"
            >
              {{ reference.title }}
            </a>
            <strong v-else>{{ reference.title }}</strong>
            <span>{{ reference.source_organization }} · {{ reference.locator }}</span>
          </li>
        </ul>
      </div>
    </article>
  </section>
</template>
