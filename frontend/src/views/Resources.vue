<template>
  <a-card>
    <a-space direction="vertical" fill>
      <a-space>
        <a-input
          v-model="q"
          placeholder="搜索资源"
          allow-clear
          @press-enter="loadSearch"
        />
        <a-button type="primary" @click="load">刷新</a-button>
      </a-space>
      <a-table
        :data="rows"
        :loading="loading"
        row-key="id"
        :pagination="{ pageSize: 50 }"
      >
        <template #columns>
          <a-table-column title="ID" data-index="id" />
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="大小" data-index="size" />
          <a-table-column title="状态" data-index="status" />
          <a-table-column title="创建时间" data-index="created_at" />
        </template>
      </a-table>
    </a-space>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Message } from "@arco-design/web-vue";
import { catalog } from "../api";

const rows = ref<any[]>([]);
const loading = ref(false);
const q = ref("");

async function load() {
  loading.value = true;
  try {
    const response = await catalog.list({ page: 1, size: 50 });
    rows.value = response.data?.data?.items || response.data?.items || [];
  } catch (error: any) {
    Message.error(error.response?.data?.detail || "加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadSearch() {
  if (!q.value) {
    await load();
    return;
  }
  const response = await catalog.search({ q: q.value, limit: 100 });
  rows.value = response.data?.data || response.data || [];
}

onMounted(load);
</script>
