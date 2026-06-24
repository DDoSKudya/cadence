<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowPathIcon, ExclamationTriangleIcon, PlusIcon, TagIcon, TrashIcon, XMarkIcon } from "@heroicons/vue/24/outline";

import ConfirmDialog from "@/components/ConfirmDialog.vue";
import ColumnColorField from "@/features/settings/components/ColumnColorField.vue";
import {
  createSettingsTag,
  deleteSettingsTag,
  fetchSettingsTags,
  updateSettingsTag,
  type SettingsTag,
} from "@/features/settings/tags-api";
import { colorToHex } from "@/lib/column-color";

const { t } = useI18n();

const tags = ref<SettingsTag[]>([]);
const loading = ref(true);
const loadFailed = ref(false);
const loadError = ref("");
const saving = ref(false);
const deletingId = ref<number | null>(null);
const editorMode = ref<"create" | "edit" | null>(null);
const editingTagId = ref<number | null>(null);
const draftName = ref("");
const draftColor = ref("slate");
const formError = ref("");
const confirmOpen = ref(false);
const pendingDeleteTag = ref<SettingsTag | null>(null);

const sortedTags = computed(() =>
  [...tags.value].sort((left, right) => left.name.localeCompare(right.name)),
);

const isEditorOpen = computed(() => editorMode.value !== null);

const editingTag = computed(() =>
  editingTagId.value === null
    ? null
    : tags.value.find((tag) => tag.id === editingTagId.value) ?? null,
);

const editorTitle = computed(() => {
  if (editorMode.value === "create") {
    return t("settings.tagsCreateTitle");
  }
  if (editorMode.value === "edit") {
    return t("settings.tagsEditTitle");
  }
  return "";
});

const previewName = computed(() => draftName.value.trim() || t("settings.tagsPreviewPlaceholder"));

async function loadTags() {
  loading.value = true;
  loadFailed.value = false;
  loadError.value = "";
  try {
    tags.value = await fetchSettingsTags();
  } catch (error) {
    loadFailed.value = true;
    loadError.value = error instanceof Error ? error.message : t("errors.loadTags");
    tags.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadTags();
});

function onEscape(event: KeyboardEvent) {
  if (event.key === "Escape" && isEditorOpen.value) {
    closeEditor();
  }
}

watch(isEditorOpen, (open) => {
  if (open) {
    document.addEventListener("keydown", onEscape);
  } else {
    document.removeEventListener("keydown", onEscape);
  }
});

onUnmounted(() => {
  document.removeEventListener("keydown", onEscape);
});

watch(draftColor, () => {
  formError.value = "";
});

function tagChipStyle(color: string) {
  const hex = colorToHex(color);
  return {
    color: hex,
    borderColor: `color-mix(in srgb, ${hex} 30%, var(--color-border))`,
    background: `color-mix(in srgb, ${hex} 14%, var(--color-surface))`,
  };
}

function openCreate() {
  resetEditor();
  editorMode.value = "create";
}

function openEdit(tag: SettingsTag) {
  editorMode.value = "edit";
  editingTagId.value = tag.id;
  draftName.value = tag.name;
  draftColor.value = tag.color || "slate";
  formError.value = "";
}

function resetEditor() {
  editorMode.value = null;
  editingTagId.value = null;
  draftName.value = "";
  draftColor.value = "slate";
  formError.value = "";
}

function closeEditor(force = false) {
  if (saving.value && !force) {
    return;
  }
  resetEditor();
}

async function submitEditor() {
  const name = draftName.value.trim();
  if (!name) {
    formError.value = t("settings.tagsNameRequired");
    return;
  }

  saving.value = true;
  formError.value = "";
  try {
    if (editorMode.value === "create") {
      const created = await createSettingsTag({ name, color: draftColor.value });
      tags.value = [...tags.value, created];
      closeEditor(true);
    } else if (editingTagId.value !== null) {
      const updated = await updateSettingsTag(editingTagId.value, {
        name,
        color: draftColor.value,
      });
      tags.value = tags.value.map((tag) => (tag.id === updated.id ? updated : tag));
      closeEditor(true);
    }
  } catch (saveError) {
    formError.value = saveError instanceof Error ? saveError.message : t("errors.saveTag");
  } finally {
    saving.value = false;
  }
}

function requestDelete(tag: SettingsTag) {
  pendingDeleteTag.value = tag;
  confirmOpen.value = true;
}

function cancelDelete() {
  if (deletingId.value !== null) {
    return;
  }
  pendingDeleteTag.value = null;
}

async function confirmDelete() {
  const tag = pendingDeleteTag.value;
  if (!tag) {
    return;
  }

  deletingId.value = tag.id;
  formError.value = "";
  try {
    await deleteSettingsTag(tag.id);
    tags.value = tags.value.filter((item) => item.id !== tag.id);
    if (editingTagId.value === tag.id) {
      closeEditor();
    }
    confirmOpen.value = false;
    pendingDeleteTag.value = null;
  } catch (deleteError) {
    formError.value =
      deleteError instanceof Error ? deleteError.message : t("errors.deleteTag");
    confirmOpen.value = false;
    pendingDeleteTag.value = null;
  } finally {
    deletingId.value = null;
  }
}
</script>

<template>
  <div class="tags-settings-root">
    <section class="settings-panel tags-settings-panel" role="region" :aria-label="t('settings.tagsTab')">
    <header class="settings-panel-header columns-list-header">
      <div class="columns-list-header-main">
        <p class="drawer-eyebrow">{{ t("settings.tagsTabEyebrow") }}</p>
        <h2 class="settings-panel-title">{{ t("settings.tagsTab") }}</h2>
        <p class="tags-settings-hint">{{ t("settings.tagsTabHint") }}</p>
      </div>
      <button
        v-if="!loadFailed && !loading && sortedTags.length"
        class="btn-primary board-action-btn"
        type="button"
        @click="openCreate"
      >
        <PlusIcon class="icon-sm" />
        {{ t("settings.tagsAdd") }}
      </button>
    </header>

    <div class="settings-panel-body tags-settings-body">
      <Transition name="scheme-body-swap" mode="out-in">
        <div v-if="loading" key="loading" class="loading-state tags-settings-loading">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-(--color-text-secondary)">{{ t("common.loading") }}</p>
        </div>

        <div v-else-if="loadFailed" key="error" class="tags-settings-error">
          <span class="tags-settings-error-icon" aria-hidden="true">
            <ExclamationTriangleIcon class="size-7" />
          </span>
          <h3 class="tags-settings-error-title">{{ t("settings.tagsLoadFailedTitle") }}</h3>
          <p class="tags-settings-error-text">
            {{ loadError || t("errors.loadTags") }}
          </p>
          <button class="btn-ghost px-4 py-2 text-sm" type="button" @click="loadTags">
            <ArrowPathIcon class="icon-sm" />
            {{ t("common.retry") }}
          </button>
        </div>

        <div v-else key="content">
        <p v-if="sortedTags.length" class="tags-settings-list-hint">
          {{ t("settings.tagsListHint") }}
        </p>

        <div v-if="sortedTags.length" class="tags-cloud-panel">
          <ul class="tags-cloud" role="list">
            <li
              v-for="(tag, index) in sortedTags"
              :key="tag.id"
              class="scheme-stagger-item"
              :style="{ '--scheme-item-delay': `${index * 40}ms` }"
              role="listitem"
            >
              <button
                type="button"
                class="tags-cloud-chip"
                :class="{ 'tags-cloud-chip-active': editingTagId === tag.id }"
                :style="tagChipStyle(tag.color)"
                :aria-label="t('settings.tagsEditCard', { name: tag.name })"
                @click="openEdit(tag)"
              >
                <TagIcon class="size-3.5 shrink-0" aria-hidden="true" />
                {{ tag.name }}
              </button>
            </li>
          </ul>
        </div>

        <div v-else class="tags-settings-empty">
          <span class="tags-settings-empty-icon" aria-hidden="true">
            <TagIcon class="size-7" />
          </span>
          <h3 class="tags-settings-empty-title">{{ t("settings.tagsEmptyTitle") }}</h3>
          <p class="tags-settings-empty-text">{{ t("settings.tagsEmpty") }}</p>
          <button class="btn-ghost px-4 py-2 text-sm" type="button" @click="openCreate">
            <PlusIcon class="icon-sm" />
            {{ t("settings.tagsAddFirst") }}
          </button>
        </div>
        </div>
      </Transition>
    </div>
  </section>

  <Teleport to="body">
    <Transition name="slide-panel">
      <div
        v-if="isEditorOpen"
        class="drawer-backdrop"
        role="presentation"
        @click.self="() => closeEditor()"
      >
        <aside
          class="drawer-panel drawer-panel-narrow"
          role="dialog"
          aria-modal="true"
          :aria-label="editorTitle"
        >
          <header class="drawer-header">
            <div>
              <p class="drawer-eyebrow">
                {{
                  editorMode === "create"
                    ? t("settings.tagsCreateEyebrow")
                    : t("settings.tagsEditEyebrow")
                }}
              </p>
              <h2 class="drawer-title">{{ editorTitle }}</h2>
            </div>
            <button
              class="icon-btn"
              type="button"
              :aria-label="t('common.close')"
              :disabled="saving"
              @click="() => closeEditor()"
            >
              <XMarkIcon class="icon-sm" />
            </button>
          </header>

          <form class="drawer-body task-form" @submit.prevent="submitEditor">
            <p v-if="formError" class="alert-error">{{ formError }}</p>

            <div class="tags-settings-preview-block">
              <span class="tags-settings-preview-label">{{ t("settings.tagsPreviewLabel") }}</span>
              <span class="tags-settings-preview-chip" :style="tagChipStyle(draftColor)">
                <TagIcon class="size-3.5" aria-hidden="true" />
                {{ previewName }}
              </span>
            </div>

            <label class="form-field">
              <span class="form-label">{{ t("settings.tagsNameLabel") }}</span>
              <input
                v-model="draftName"
                class="field px-3 py-2"
                type="text"
                maxlength="50"
                :placeholder="t('settings.tagsNamePlaceholder')"
                autofocus
              />
            </label>

            <div class="form-field">
              <span class="form-label">{{ t("settings.tagsColorLabel") }}</span>
              <ColumnColorField v-model="draftColor" />
            </div>

            <p v-if="editingTag?.slug" class="tags-settings-slug-note">
              {{ t("settings.tagsSlugLabel") }}
              <code>{{ editingTag.slug }}</code>
            </p>
          </form>

          <footer class="drawer-footer tags-settings-drawer-footer">
            <button
              v-if="editorMode === 'edit' && editingTag"
              class="btn-ghost tags-settings-delete-btn px-3 py-2 text-sm"
              type="button"
              :disabled="saving || deletingId === editingTag.id"
              @click="requestDelete(editingTag)"
            >
              <TrashIcon class="icon-sm" />
              {{ t("common.delete") }}
            </button>

            <div class="tags-settings-drawer-actions">
              <button
                class="btn-primary px-4 py-2 text-sm"
                type="button"
                :disabled="saving"
                @click="submitEditor"
              >
                {{
                  saving
                    ? t("common.saving")
                    : editorMode === "create"
                      ? t("common.create")
                      : t("common.save")
                }}
              </button>
            </div>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>

  <ConfirmDialog
    v-model="confirmOpen"
    :title="$t('settings.tagsDeleteConfirmTitle')"
    :message="
      pendingDeleteTag
        ? $t('settings.tagsDeleteConfirm', { name: pendingDeleteTag.name })
        : ''
    "
    :confirm-label="$t('common.delete')"
    :loading="deletingId !== null"
    danger
    @confirm="confirmDelete"
    @cancel="cancelDelete"
  />
  </div>
</template>
