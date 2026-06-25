<script setup lang="ts">
defineProps<{
  iconClass?: string;
}>();
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 512 512"
    fill="none"
    :class="iconClass"
    aria-hidden="true"
  >
    <rect width="512" height="512" rx="112" fill="#5b6ee8" />
    <g stroke="#ffffff" stroke-width="26" fill="none">
      <circle cx="196" cy="196" r="36" />
      <circle cx="316" cy="196" r="36" />
      <circle cx="196" cy="316" r="36" />
      <circle cx="316" cy="316" r="36" />
    </g>
  </svg>
</template>
