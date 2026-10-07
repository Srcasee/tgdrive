<template>
  <div class="snow-page">
    <a-card title="Telegram 对话">
      <a-space class="toolbar">
        <a-select v-model="accountId" placeholder="选择账号" style="width: 260px" @change="load">
          <a-option v-for="item in accounts" :key="item.id" :value="item.id">{{ item.id }} - {{ item.telegram_username || item.session_name }}</a-option>
        </a-select>
      </a-space>
      <a-table :data="rows" :loading="loading" row-key="telegram_chat_id">
        <template #columns>
          <a-table-column title="Chat ID" data-index="telegram_chat_id" />
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="类型" data-index="type" />
          <a-table-column title="来源状态">
            <template #cell="{ record }">{{ record.source_enabled ? "已启用" : "未启用" }}</template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-popconfirm content="确定删除该对话吗？" @ok="remove(record)">
                <a-button size="small" status="danger" :disabled="record.source_enabled">删除</a-button>
              </a-popconfirm>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { getAccountsAPI, getDialogsAPI, deleteDialogAPI } from "@/api/modules/tgdrive";
const accounts = ref<any[]>([]); const rows = ref<any[]>([]); const loading = ref(false); const accountId = ref<number>();
const loadAccounts = async () => { accounts.value = (await getAccountsAPI()).data || []; if (!accountId.value && accounts.value.length) { accountId.value = accounts.value[0].id; load(); } };
const load = async () => { if (!accountId.value) return; loading.value = true; try { rows.value = (await getDialogsAPI(accountId.value)).data || []; } finally { loading.value = false; } };
const remove = async (row: any) => { await deleteDialogAPI(accountId.value!, row.telegram_chat_id); await load(); };
loadAccounts();
</script>

<style scoped>.toolbar { margin-bottom: 16px; }</style>
