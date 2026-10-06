<template>
  <a-card>
    <a-space direction="vertical" fill>
      <a-space>
        <a-button @click="load">刷新</a-button>
        <a-button type="primary" @click="reconnect">重连 Telegram</a-button>
      </a-space>
      <a-table :data="rows" :loading="loading">
        <template #columns>
          <a-table-column title="ID" data-index="id" />
          <a-table-column title="账号" data-index="name" />
          <a-table-column title="用户名" data-index="telegram_username" />
          <a-table-column title="启用">
            <template #cell="{ record }">
              <a-switch v-model="record.enabled" @change="(v) => toggle(record, v)" />
            </template>
          </a-table-column>
          <a-table-column title="状态">
            <template #cell="{ record }">{{ record.info_error ? "异常" : "正常" }}</template>
          </a-table-column>
        </template>
      </a-table>
    </a-space>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Message } from "@arco-design/web-vue";
import { telegram } from "../api";

const rows = ref<any[]>([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    rows.value = (await telegram.accounts()).data;
  } finally {
    loading.value = false;
  }
}

async function toggle(record: any, enabled: boolean) {
  try {
    await telegram.accountEnabled(record.id, enabled);
    Message.success("状态已更新");
  } catch {
    record.enabled = !enabled;
  }
}

async function reconnect() {
  await telegram.reconnect();
  Message.success("已触发重连");
  await load();
}

onMounted(load);
</script>
