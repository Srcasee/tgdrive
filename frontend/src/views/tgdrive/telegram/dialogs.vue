<template>
  <div class="snow-page">
    <a-card title="群组/频道管理">
      <a-table :data="rows" :loading="loading" row-key="row_key">
        <template #columns>
          <a-table-column title="账号" data-index="account_id" />
          <a-table-column title="Chat ID" data-index="telegram_chat_id" />
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="用户名" data-index="username">
            <template #cell="{ record }">{{ record.username ? `@${record.username}` : "-" }}</template>
          </a-table-column>
          <a-table-column title="类型" data-index="entity_type" />
          <a-table-column title="群组" data-index="is_group">
            <template #cell="{ record }">{{ record.is_group ? "是" : "否" }}</template>
          </a-table-column>
          <a-table-column title="频道" data-index="is_channel">
            <template #cell="{ record }">{{ record.is_channel ? "是" : "否" }}</template>
          </a-table-column>
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
import { getDialogsAPI, deleteDialogAPI } from "@/api/modules/tgdrive";

const rows = ref<any[]>([]);
const loading = ref(false);

const load = async () => {
  loading.value = true;
  try {
    const data = (await getDialogsAPI()).data || [];
    rows.value = data.map((item: any) => ({
      ...item,
      row_key: `${item.account_id}:${item.telegram_chat_id}`
    }));
  } finally {
    loading.value = false;
  }
};

const remove = async (row: any) => {
  await deleteDialogAPI(row.account_id, row.telegram_chat_id);
  await load();
};

load();
</script>
