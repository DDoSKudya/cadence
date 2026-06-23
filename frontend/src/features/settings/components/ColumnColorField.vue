<script setup lang="ts">
import { computed, ref, watch } from "vue";

import {
  columnColorOptions,
  colorSwatchClass,
  colorToHex,
  isHexColor,
} from "@/lib/column-color";

const model = defineModel<string>({ required: true });

const customHex = ref("#64748b");
const options = computed(() => columnColorOptions());

watch(
  () => model.value,
  (color) => {
    customHex.value = colorToHex(color);
  },
  { immediate: true },
);

function pickPreset(value: string) {
  model.value = value;
}

function applyCustom() {
  model.value = customHex.value.toLowerCase();
}
</script>

<template>
  <div class="column-color-field">
    <div class="color-drawer-grid" role="radiogroup" :aria-label="$t('colors.columnColor')">
      <button
        v-for="option in options"
        :key="option.value"
        type="button"
        class="color-drawer-option"
        :class="{ 'color-drawer-option-active': model === option.value }"
        @click="pickPreset(option.value)"
      >
        <span
          class="color-swatch color-swatch-lg"
          :class="colorSwatchClass(option.value)"
        />
        <span class="color-drawer-option-label">{{ option.label }}</span>
      </button>
    </div>

    <div class="color-custom">
      <input
        v-model="customHex"
        class="color-custom-input"
        type="color"
        :aria-label="$t('colors.customColor')"
        @input="applyCustom"
      />
      <span class="color-custom-value">{{ customHex.toUpperCase() }}</span>
    </div>
    <p v-if="isHexColor(model)" class="color-custom-note">{{ $t("colors.customSelected") }}</p>
  </div>
</template>
