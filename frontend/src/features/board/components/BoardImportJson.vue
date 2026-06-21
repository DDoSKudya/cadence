<script setup lang="ts">
import { ref } from "vue";
import { ArrowUpTrayIcon } from "@heroicons/vue/24/outline";

import ImportJsonModal from "@/features/imports/components/ImportJsonModal.vue";
import { useBoardStore } from "@/features/board/stores/board";

const board = useBoardStore();
const open = ref(false);

async function onImported() {
  await board.loadBoard();
}
</script>

<template>
  <button class="btn-ghost px-3 py-2 text-sm" type="button" @click="open = true">
    <ArrowUpTrayIcon class="icon-sm" />
    Импорт задач
  </button>

  <ImportJsonModal v-model:open="open" @imported="onImported" />
</template>
