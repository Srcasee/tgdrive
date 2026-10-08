<template>
  <div class="snow-page">
    <a-card title="Source管理">
      <template #extra><a-button type="primary" @click="open = true">新增来源</a-button></template>
      <a-table :data="rows" :loading="loading" row-key="id">
        <template #columns>
          <a-table-column title="Chat ID" data-index="telegram_chat_id" />
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="状态">
            <template #cell="{ record }">
              <a-switch v-model="record.enabled" @change="toggle(record)" />
            </template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-popconfirm content="确定删除来源吗？" @ok="remove(record)">
                <a-button size="small" status="danger">删除</a-button>
              </a-popconfirm>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <a-modal v-model:visible="open" title="新增来源" @ok="create">
      <a-form :model="form">
        <a-form-item label="账号">
          <a-select v-model="form.account_id">
            <a-option
              v-for="item in accounts"
              :key="item.id"
              :value="item.id"
            >
              {{ item.id }} - {{ item.telegram_username || item.session_name }}
            </a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="Chat ID"><a-input-number v-model="form.telegram_chat_id" /></a-form-item>
        <a-form-item label="名称"><a-input v-model="form.name" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  getAccountsAPI,
  getSourcesAPI,
  createSourceAPI,
  setSourceEnabledAPI,
  deleteSourceAPI
} from "@/api/modules/tgdrive";

const rows = ref<any[]>([]);
const accounts = ref<any[]>([]);
const loading = ref(false);
const open = ref(false);
const form = ref({ account_id: 0, telegram_chat_id: 0, name: "" });

const load = async () => {
  loading.value = true;
  try {
    rows.value = (await getSourcesAPI()).data || [];
  } finally {
    loading.value = false;
  }
};

const toggle = async (row: any) => {
  await setSourceEnabledAPI(row.id, row.enabled);
  await load();
};

const remove = async (row: any) => {
  await deleteSourceAPI(row.id);
  await load();
};

const create = async () => {
  await createSourceAPI(form.value);
  open.value = false;
  form.value = { account_id: 0, telegram_chat_id: 0, name: "" };
  await load();
};

Promise.all([
  load(),
  getAccountsAPI().then(response => {
    accounts.value = response.data || [];
  })
]);
</script>
