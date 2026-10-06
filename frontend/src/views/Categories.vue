<template>
  <a-card>
    <a-space direction="vertical" fill>
      <a-space>
        <a-input v-model="name" placeholder="新分类名称" />
        <a-button type="primary" @click="create">新增</a-button>
        <a-button @click="load">刷新</a-button>
      </a-space>
      <a-table :data="rows">
        <template #columns>
          <a-table-column title="ID" data-index="id" />
          <a-table-column title="名称" data-index="name" />
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-popconfirm content="确定删除？" @ok="remove(record.id)">
                <a-button status="danger" type="text">删除</a-button>
              </a-popconfirm>
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
import { admin } from "../api";

const rows = ref<any[]>([]);
const name = ref("");

async function load() {
  const response = await admin.categories();
  rows.value = response.data || [];
}

async function create() {
  if (!name.value.trim()) return;
  await admin.createCategory(name.value.trim());
  name.value = "";
  Message.success("已创建");
  await load();
}

async function remove(id: number) {
  await admin.deleteCategory(id);
  Message.success("已删除");
  await load();
}

onMounted(load);
</script>
