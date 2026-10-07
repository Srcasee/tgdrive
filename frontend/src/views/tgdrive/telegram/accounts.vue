<template>
  <div class="snow-page">
    <a-card title="Telegram 账号">
      <a-table :data="rows" :loading="loading" row-key="id">
        <template #columns>
          <a-table-column title="ID" data-index="id" />
          <a-table-column title="会话" data-index="session_name" />
          <a-table-column title="用户名" data-index="telegram_username" />
          <a-table-column title="Telegram ID" data-index="telegram_user_id" />
          <a-table-column title="手机号" data-index="telegram_phone" />
          <a-table-column title="状态">
            <template #cell="{ record }">
              <a-switch v-model="record.enabled" @change="toggle(record)" />
            </template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-button size="small" @click="info(record)">刷新信息</a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Message } from "@arco-design/web-vue";
import { getAccountsAPI, setAccountEnabledAPI } from "@/api/modules/tgdrive";
const rows = ref<any[]>([]);
const loading = ref(false);
const load = async () => { loading.value = true; try { rows.value = (await getAccountsAPI()).data || []; } finally { loading.value = false; } };
const toggle = async (row: any) => {
  try { await setAccountEnabledAPI(row.id, row.enabled); await load(); Message.success("账号状态已更新"); }
  catch { row.enabled = !row.enabled; }
};
const info = async (row: any) => {
  const fresh = (await getAccountsAPI()).data?.find((x: any) => x.id === row.id);
  if (fresh) Object.assign(row, fresh);
};
load();
</script>
