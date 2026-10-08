<template>
  <div class="snow-page">
    <a-card title="群组/频道管理">
      <a-table :data="rows" :loading="loading" row-key="row_key" :pagination="{ pageSize: 20 }">
        <template #columns>
          <a-table-column title="Chat ID" data-index="telegram_chat_id" />
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="用户名" data-index="username">
            <template #cell="{ record }">{{ record.username ? `@${record.username}` : "-" }}</template>
          </a-table-column>
        
          <a-table-column title="状态">
            <template #cell="{ record }">
              <a-switch v-model="record.source_enabled" :loading="record.toggling" @change="toggle(record)" />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { getDialogsAPI, setDialogEnabledAPI } from "@/api/modules/tgdrive";

const rows = ref<any[]>([]);
const loading = ref(false);

const load = async () => {
  loading.value = true;
  try {
    const data = (await getDialogsAPI()).data || [];
    rows.value = data
      .filter((item: any) => item.entity_type === "Channel")
      .map((item: any) => ({
        ...item,
        source_enabled: Boolean(item.source_enabled),
        toggling: false,
        row_key: `${item.account_id}:${item.telegram_chat_id}`
      }));
  } finally {
    loading.value = false;
  }
};

const toggle = async (row: any) => {
  row.toggling = true;
  try {
    await setDialogEnabledAPI(row.account_id, row.telegram_chat_id, row.source_enabled);
  } catch (error) {
    row.source_enabled = !row.source_enabled;
    throw error;
  } finally {
    row.toggling = false;
  }
};

load();
</script>
