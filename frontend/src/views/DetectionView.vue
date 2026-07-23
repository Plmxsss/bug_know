<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useDetectionStore } from '../stores/detection'

const acceptedTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])
const maxBytes = 10 * 1024 * 1024

const detectionStore = useDetectionStore()
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')
const selectionError = ref('')
const isDragging = ref(false)

function clearPreview(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

function selectFile(file: File | undefined): void {
  selectionError.value = ''
  detectionStore.reset()
  clearPreview()

  if (!file) {
    selectedFile.value = null
    return
  }
  if (!acceptedTypes.has(file.type)) {
    selectedFile.value = null
    selectionError.value = '请选择 JPEG、PNG 或 WebP 图片。'
    return
  }
  if (file.size > maxBytes) {
    selectedFile.value = null
    selectionError.value = '图片不能超过 10 MB。'
    return
  }

  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
}

function handleFileInput(event: Event): void {
  const input = event.target as HTMLInputElement
  selectFile(input.files?.[0])
  input.value = ''
}

function handleDrop(event: DragEvent): void {
  isDragging.value = false
  selectFile(event.dataTransfer?.files[0])
}

async function submitDetection(): Promise<void> {
  if (selectedFile.value) {
    await detectionStore.detect(selectedFile.value)
  }
}

onBeforeUnmount(clearPreview)
</script>

<template>
  <section class="detection-page">
    <div class="detection-heading">
      <p class="eyebrow">PEST DETECTION</p>
      <h1>上传一张害虫图片</h1>
      <p>支持 JPEG、PNG 和 WebP，单张图片不超过 10 MB。</p>
    </div>

    <div class="detection-workspace">
      <div class="upload-column">
        <label
          class="upload-zone"
          :class="{ dragging: isDragging, selected: previewUrl }"
          @dragenter.prevent="isDragging = true"
          @dragover.prevent
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
        >
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            @change="handleFileInput"
          />
          <img v-if="previewUrl" :src="previewUrl" alt="待检测图片预览" />
          <span v-else class="upload-placeholder">
            <strong>选择图片或拖放到这里</strong>
            <small>浏览器先预览，提交后由 FastAPI 再次严格校验</small>
          </span>
        </label>

        <div v-if="selectedFile" class="selected-file">
          <span>{{ selectedFile.name }}</span>
          <span>{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</span>
        </div>

        <p v-if="selectionError" class="form-error">{{ selectionError }}</p>
        <p v-if="detectionStore.errorMessage" class="form-error">
          {{ detectionStore.errorMessage }}
        </p>

        <button
          type="button"
          class="detect-action"
          :disabled="!selectedFile || detectionStore.isSubmitting"
          @click="submitDetection"
        >
          {{
            detectionStore.isSubmitting
              ? '正在运行 YOLO…'
              : '开始识别'
          }}
        </button>
      </div>

      <div class="result-column">
        <div v-if="!detectionStore.result" class="empty-result">
          <span>RESULT</span>
          <h2>检测结果将在这里显示</h2>
          <p>提交图片后，可以查看标注图、害虫类别、置信度和位置。</p>
        </div>

        <template v-else>
          <div class="result-summary">
            <div>
              <span>任务编号</span>
              <strong>#{{ detectionStore.result.task_id }}</strong>
            </div>
            <div>
              <span>目标数量</span>
              <strong>{{ detectionStore.result.detections.length }}</strong>
            </div>
            <div>
              <span>推理耗时</span>
              <strong>{{ detectionStore.result.inference_ms.toFixed(1) }} ms</strong>
            </div>
          </div>

          <img
            class="annotated-image"
            :src="detectionStore.result.annotated_image_url"
            alt="YOLO 标注结果"
          />

          <ul class="detection-list">
            <li
              v-for="(detection, index) in detectionStore.result.detections"
              :key="`${detection.class_id}-${index}`"
            >
              <div>
                <strong>{{ detection.common_name ?? detection.class_name }}</strong>
                <small>类别 ID {{ detection.class_id }}</small>
              </div>
              <span>{{ (detection.confidence * 100).toFixed(1) }}%</span>
            </li>
          </ul>
        </template>
      </div>
    </div>
  </section>
</template>
