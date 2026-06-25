<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowUpTrayIcon,
  ExclamationCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

import { uploadImport } from "@/features/imports/api";
import {
  parseImportFile,
  priorityLabel,
  type ImportPreview,
} from "@/features/imports/parse-import";
import { useActionFeedback } from "@/composables/useActionFeedback";

const open = defineModel<boolean>("open", { default: false });
const { t } = useI18n();
const feedback = useActionFeedback();

const emit = defineEmits<{
  imported: [];
}>();

const previews = ref<ImportPreview[]>([]);
const parsing = ref(false);
const importing = ref(false);
const dragging = ref(false);
const error = ref("");
const fileInput = ref<HTMLInputElement | null>(null);

const validPreviews = computed(() =>
  previews.value.filter(
    (item): item is Extract<ImportPreview, { status: "valid" }> => item.status === "valid",
  ),
);

const invalidPreviews = computed(() =>
  previews.value.filter(
    (item): item is Extract<ImportPreview, { status: "invalid" }> => item.status === "invalid",
  ),
);

const totalTasks = computed(() =>
  validPreviews.value.reduce((sum, item) => sum + item.tasks.length, 0),
);

const hasPreview = computed(() => previews.value.length > 0);
const busy = computed(() => parsing.value || importing.value);

function resetState() {
  previews.value = [];
  parsing.value = false;
  importing.value = false;
  dragging.value = false;
  error.value = "";
}

function close() {
  if (busy.value) {
    return;
  }
  open.value = false;
}

function openFilePicker() {
  fileInput.value?.click();
}

function isJsonFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".json");
}

async function handleFiles(fileList: FileList | File[] | null | undefined) {
  const files = Array.from(fileList ?? []).filter(isJsonFile);
  if (files.length === 0) {
    if ((fileList?.length ?? 0) > 0) {
      error.value = t("imports.jsonOnly");
    }
    return;
  }

  parsing.value = true;
  error.value = "";

  const parsed = await Promise.all(files.map((file) => parseImportFile(file)));
  previews.value.push(...parsed);
  parsing.value = false;
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement;
  void handleFiles(input.files);
  input.value = "";
}

function onDragOver(event: DragEvent) {
  event.preventDefault();
  dragging.value = true;
}

function onDragLeave() {
  dragging.value = false;
}

function onDrop(event: DragEvent) {
  event.preventDefault();
  dragging.value = false;
  void handleFiles(event.dataTransfer?.files);
}

function removePreview(id: string) {
  previews.value = previews.value.filter((item) => item.id !== id);
}

function cancelPreview() {
  previews.value = [];
  error.value = "";
}

async function confirmImport() {
  if (validPreviews.value.length === 0) {
    return;
  }

  importing.value = true;
  error.value = "";

  const failedMessages: string[] = [];

  for (const preview of validPreviews.value) {
    try {
      const result = await uploadImport(preview.file);
      if (result.status === "succeeded") {
        continue;
      }
      if (result.status === "skipped_duplicate") {
        continue;
      } else {
        failedMessages.push(`${preview.file.name}: ${result.error_message || t("imports.importError")}`);
      }
    } catch (uploadError) {
      const message =
        uploadError instanceof Error ? uploadError.message : t("imports.importError");
      failedMessages.push(`${preview.file.name}: ${message}`);
    }
  }

  previews.value = [];
  importing.value = false;

  if (failedMessages.length > 0) {
    error.value = failedMessages.join("\n");
    feedback.error(failedMessages.join("\n"));
    return;
  }

  feedback.successKey("toast.importCompleted");

  emit("imported");
  resetState();
  open.value = false;
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    close();
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener("keydown", onDocumentKeydown);
    return;
  }
  document.removeEventListener("keydown", onDocumentKeydown);
  resetState();
});

onUnmounted(() => {
  document.removeEventListener("keydown", onDocumentKeydown);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="open"
        class="modal-backdrop"
        role="presentation"
        @click.self="close"
      >
        <section
          class="modal-panel imports-modal-panel"
          role="dialog"
          aria-labelledby="import-json-title"
          aria-modal="true"
        >
          <header class="modal-header">
            <h2 id="import-json-title" class="modal-title">{{ $t("imports.title") }}</h2>
            <button
              class="icon-btn"
              type="button"
              :aria-label="$t('common.close')"
              :disabled="busy"
              @click="close"
            >
              <XMarkIcon class="icon-sm" />
            </button>
          </header>

          <div class="imports-modal-body">
            <input
              ref="fileInput"
              accept=".json,application/json"
              class="sr-only"
              multiple
              type="file"
              @change="onFileInput"
            />

            <button
              class="imports-dropzone imports-dropzone-modal"
              :class="{
                'imports-dropzone-active': dragging,
                'imports-dropzone-busy': busy,
                'imports-dropzone-compact': hasPreview,
              }"
              type="button"
              :disabled="busy"
              @click="openFilePicker"
              @dragover="onDragOver"
              @dragleave="onDragLeave"
              @drop="onDrop"
            >
              <span class="imports-dropzone-icon">
                <ArrowUpTrayIcon v-if="!busy" class="size-7" />
                <span v-else class="loading-spinner" aria-hidden="true" />
              </span>
              <span class="imports-dropzone-title">
                {{
                  parsing
                    ? $t("imports.parsing")
                    : importing
                      ? $t("imports.importing")
                      : $t("imports.dropTitle")
                }}
              </span>
              <span class="imports-dropzone-text">
                {{
                  hasPreview
                    ? $t("imports.addMore")
                    : $t("imports.dropText")
                }}
              </span>
            </button>

            <p v-if="error" class="alert-error shrink-0 whitespace-pre-line">{{ error }}</p>

            <section v-if="hasPreview" class="imports-preview">
              <div class="imports-preview-summary">
                <p>
                  {{
                    $t("imports.summary", {
                      files: previews.length,
                      ready: validPreviews.length,
                      failed: invalidPreviews.length,
                      tasks: totalTasks,
                    })
                  }}
                </p>
              </div>

              <article
                v-for="item in previews"
                :key="item.id"
                class="imports-file-card"
                :class="{ 'imports-file-card-invalid': item.status === 'invalid' }"
              >
                <header class="imports-file-card-header">
                  <div>
                    <h3 class="imports-file-card-title">{{ item.file.name }}</h3>
                    <p v-if="item.status === 'valid'" class="imports-file-card-meta">
                      {{ $t("imports.idempotencyKey", { key: item.idempotencyKey }) }}
                      <span v-if="item.week"> · {{ $t("imports.week", { week: item.week }) }}</span>
                    </p>
                  </div>
                  <div class="imports-file-card-actions">
                    <span
                      class="imports-file-badge"
                      :class="
                        item.status === 'valid'
                          ? 'imports-file-badge-valid'
                          : 'imports-file-badge-invalid'
                      "
                    >
                      {{ item.status === "valid" ? $t("imports.ready") : $t("imports.error") }}
                    </span>
                    <button
                      class="imports-file-remove"
                      type="button"
                      :aria-label="$t('imports.removeFile')"
                      :disabled="busy"
                      @click="removePreview(item.id)"
                    >
                      <XMarkIcon class="size-4" />
                    </button>
                  </div>
                </header>

                <p v-if="item.status === 'invalid'" class="imports-file-error">
                  <ExclamationCircleIcon class="size-4 shrink-0" />
                  {{ item.error }}
                </p>

                <div v-else class="imports-table-wrap">
                  <table class="imports-table">
                    <thead>
                      <tr>
                        <th>{{ $t("imports.task") }}</th>
                        <th>{{ $t("imports.column") }}</th>
                        <th>{{ $t("imports.priority") }}</th>
                        <th>{{ $t("imports.tags") }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(task, index) in item.tasks" :key="`${item.id}-${index}`">
                        <td class="imports-filename">{{ task.title }}</td>
                        <td>{{ task.column }}</td>
                        <td>{{ priorityLabel(task.priority) }}</td>
                        <td>{{ task.tags.length > 0 ? task.tags.join(", ") : "—" }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </article>
            </section>
          </div>

          <footer v-if="hasPreview" class="modal-footer imports-modal-footer">
            <button
              class="btn-ghost px-4 py-2 text-sm disabled:opacity-60"
              type="button"
              :disabled="busy"
              @click="cancelPreview"
            >
              {{ $t("imports.clear") }}
            </button>
            <button
              class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
              type="button"
              :disabled="busy || validPreviews.length === 0"
              @click="confirmImport"
            >
              {{ $t("imports.importTasks", totalTasks) }}
            </button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
