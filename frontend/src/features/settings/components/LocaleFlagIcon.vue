<script setup lang="ts">
import type { AppLocale } from "@/features/settings/project-api";

defineProps<{
  locale: AppLocale;
}>();
</script>

<template>
  <span class="locale-flag-icon" aria-hidden="true">
    <svg
      v-if="locale === 'ru'"
      class="locale-flag-icon-svg"
      viewBox="0 0 21 15"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="21" height="15" fill="#fff" />
      <rect y="5" width="21" height="5" fill="#0039a6" />
      <rect y="10" width="21" height="5" fill="#d52b1e" />
    </svg>
    <svg
      v-else
      class="locale-flag-icon-svg"
      viewBox="0 0 21 15"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="21" height="15" fill="#012169" />
      <path d="M0 0 21 15M21 0 0 15" stroke="#fff" stroke-width="2.2" />
      <path d="M0 0 21 15M21 0 0 15" stroke="#c8102e" stroke-width="1.1" />
      <path d="M10.5 0v15M0 7.5h21" stroke="#fff" stroke-width="3.2" />
      <path d="M10.5 0v15M0 7.5h21" stroke="#c8102e" stroke-width="1.8" />
    </svg>
  </span>
</template>
