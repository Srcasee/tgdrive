<template>
  <a-card>
    <a-space direction="vertical" fill>
      <a-space>
        <a-select
          v-model="account"
          placeholder="选择账号"
          style="width: 260px"
          @change="load"
        >
          <a-option v-for="item in accounts" :key="item.id" :value="item.id">
            {{ item.name || item.username || item.id }}
          </a-option>
        </a-select>
      </a-space>
      <a-table :data="rows">
        <template #columns>
          <a-table-column title="Telegram Chat ID" data-index="telegram_chat_id" />
          <a-table-column title="名称" data-index="title" />
          <a-table-column title="类型" data-index="type" />
          <a-table-column title="可选">
            <template #cell="{ record }">{{ record.selectable ? "是" : "否" }}</template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-space>
                <a-button
                  v-if="record.selectable"
                  type="primary"
                  size="small"
                  @click="enable(record)"
                >
                  启用 Source
                </a-button>
                <a-popconfirm
                  content="删除 Dialog 管理记录？需先禁用 Source。"
                  @ok="remove(record.telegram_chat_id)"
                >
                  <a-button type="text" status="danger">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
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

const accounts = ref<any[]>([]);
const account = ref<number>();
const rows = ref<any[]>([]);

async function load() {
  if (!account.value) {
    rows.value = [];
    return;
  }
  rows.value = (await telegram.dialogs(account.value)).data;
}

async function enable(record: any) {
  try {
    await telegram.createSource({
      account_id: account.value,
      telegram_chat_id: record.telegram_chat_id,
      name: record.title || record.name || String(record.telegram_chat_id),
    });
    Message.success("Source 已启用");
    await load();
  } catch (error: any) {
    Message.error(error.response?.data?.detail || "启用 Source 失败");
  }
}

async function remove(id: number) {
  try {
    await telegram.deleteDialog(account.value!, id);
    Message.success("已删除");
    await load();
  } catch (error: any) {
    Message.error(error.response?.data?.detail || "删除失败");
  }
}

onMounted(async () => {
  accounts.value = (await telegram.accounts()).data;
  if (accounts.value[0]) {
    account.value = accounts.value[0].id;
    await load();
  }
});
</script>
