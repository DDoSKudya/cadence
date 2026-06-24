<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import {
  CheckCircleIcon,
  LockClosedIcon,
  PlusIcon,
  Squares2X2Icon,
  TrashIcon,
} from "@heroicons/vue/24/outline";

import type { BoardScheme } from "@/features/settings/types";

const props = defineProps<{
  schemes: BoardScheme[];
  activeSlug: string | null;
  columnCount: number;
  disabled?: boolean;
  creating?: boolean;
  createDisabled?: boolean;
  createDisabledTitle?: string;
}>();

const emit = defineEmits<{
  choose: [slug: string];
  create: [];
  delete: [slug: string];
}>();

const { t } = useI18n();

const sortedSchemes = computed(() =>
  [...props.schemes].sort((left, right) => {
    if (left.is_locked !== right.is_locked) {
      return left.is_locked ? -1 : 1;
    }
    return left.name.localeCompare(right.name, undefined, { sensitivity: "base" });
  }),
);

function schemeTitle(scheme: BoardScheme): string {
  if (scheme.slug === "default") {
    return t("settings.schemeDefaultName");
  }
  return scheme.name;
}

function schemeDescription(scheme: BoardScheme): string {
  if (scheme.slug === "default") {
    return t("settings.schemeDefaultDescription");
  }
  return scheme.description || t("settings.schemeCustomDescription");
}

function schemeMeta(scheme: BoardScheme): string {
  if (scheme.slug === props.activeSlug) {
    return t("settings.schemeColumnCount", { count: props.columnCount });
  }
  if (scheme.is_locked) {
    return t("settings.schemeBuiltinMeta");
  }
  return t("settings.schemeEditableMeta");
}

function onChoose(scheme: BoardScheme) {
  if (props.disabled || scheme.slug === props.activeSlug) {
    return;
  }
  emit("choose", scheme.slug);
}

function onDelete(scheme: BoardScheme) {
  if (props.disabled || scheme.is_locked || scheme.slug === props.activeSlug) {
    return;
  }
  emit("delete", scheme.slug);
}

function deleteDisabledTitle(scheme: BoardScheme): string | undefined {
  if (scheme.slug === props.activeSlug) {
    return t("settings.schemeDeleteActiveDisabled");
  }
  return t("settings.deleteScheme");
}
</script>

<template>
  <section class="scheme-picker" :aria-label="$t('settings.schemeLabel')">
    <div class="scheme-picker-head">
      <p class="scheme-picker-label">{{ $t("settings.schemeLabel") }}</p>
      <p class="scheme-picker-hint">{{ $t("settings.schemePickerHint") }}</p>
    </div>

    <div class="scheme-picker-grid" :aria-label="$t('settings.schemeLabel')">
      <div
        v-for="(scheme, index) in sortedSchemes"
        :key="scheme.slug"
        class="scheme-card-wrap scheme-stagger-item"
        :style="{ '--scheme-item-delay': `${index * 40}ms` }"
        role="presentation"
      >
        <button
          class="scheme-card"
          :class="{
            'scheme-card-active': scheme.slug === activeSlug,
            'scheme-card-locked': scheme.is_locked,
          }"
          type="button"
          :aria-pressed="scheme.slug === activeSlug"
          :disabled="disabled"
          @click="onChoose(scheme)"
        >
          <span class="scheme-card-icon" :class="{ 'scheme-card-icon-active': scheme.slug === activeSlug }">
            <LockClosedIcon v-if="scheme.is_locked" class="icon-sm" />
            <Squares2X2Icon v-else class="icon-sm" />
          </span>

          <span class="scheme-card-copy">
            <span class="scheme-card-title-row">
              <span class="scheme-card-title">{{ schemeTitle(scheme) }}</span>
              <CheckCircleIcon
                v-if="scheme.slug === activeSlug"
                class="scheme-card-check icon-sm"
                aria-hidden="true"
              />
            </span>
            <span class="scheme-card-description">{{ schemeDescription(scheme) }}</span>
            <span class="scheme-card-meta">{{ schemeMeta(scheme) }}</span>
          </span>
        </button>

        <button
          v-if="!scheme.is_locked"
          class="scheme-card-delete icon-btn"
          type="button"
          :title="deleteDisabledTitle(scheme)"
          :aria-label="deleteDisabledTitle(scheme)"
          :disabled="disabled || scheme.slug === activeSlug"
          @click="onDelete(scheme)"
        >
          <TrashIcon class="icon-sm" />
        </button>
      </div>

      <button
        class="scheme-card scheme-card-create"
        :class="{ 'scheme-card-create-open': creating }"
        type="button"
        :disabled="disabled || createDisabled"
        :title="createDisabled ? createDisabledTitle : undefined"
        @click="emit('create')"
      >
        <span class="scheme-card-icon scheme-card-icon-create">
          <PlusIcon class="icon-sm" />
        </span>
        <span class="scheme-card-copy">
          <span class="scheme-card-title">{{ $t("settings.newScheme") }}</span>
          <span class="scheme-card-description">{{ $t("settings.schemeCreateCardHint") }}</span>
        </span>
      </button>
    </div>
  </section>
</template>
