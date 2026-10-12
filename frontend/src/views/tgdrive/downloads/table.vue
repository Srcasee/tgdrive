<template>
  <div class="download-table">
    <div class="table-actions">
      <a-button status="danger" :disabled="selectedKeys.length === 0" @click="confirmDelete">
        批量删除<span v-if="selectedKeys.length">（{{ selectedKeys.length }}）</span>
      </a-button>
    </div>
    <a-table
      :data="rows"
      row-key="id"
      :row-selection="{ type: 'checkbox', showCheckedAll: true, selectedRowKeys: selectedKeys, onChange: onSelectionChange }"
      :pagination="false"
      :scroll="{ y: 'calc(100vh - 350px)' }"
    >
      <template #columns>
        <a-table-column title="文件名" data-index="filename" ellipsis tooltip />
        <a-table-column title="状态">
          <template #cell="{ record }">
            <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
          </template>
        </a-table-column>
        <a-table-column title="开始时间">
          <template #cell="{ record }">{{ formatTime(record.started_at) }}</template>
        </a-table-column>
        <a-table-column title="完成时间">
          <template #cell="{ record }">{{ formatTime(record.completed_at) }}</template>
        </a-table-column>
      </template>
    </a-table>
    <div class="pagination-bar">
      <a-pagination
        :current="page"
        :page-size="size"
        :total="total"
        show-total
        show-jumper
        @change="$emit('page-change', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Modal } from "@arco-design/web-vue";

const props = defineProps<{
  rows: any[];
  status: "active" | "completed" | "failed";
  page: number;
  size: number;
  total: number;
}>();
const emit = defineEmits<{ "page-change": [page: number]; "bulk-delete": [ids: number[]] }>();
const selectedKeys = ref<number[]>([]);

watch(() => [props.rows, props.status, props.page], () => {
  selectedKeys.value = [];
});

const onSelectionChange = (keys: (string | number)[]) => {
  selectedKeys.value = keys.map(Number);
};
const confirmDelete = () => {
  const ids = [...selectedKeys.value];
  if (!ids.length) return;
  Modal.warning({
    title: "确认批量删除",
    content: `确定删除选中的 ${ids.length} 条下载记录吗？此操作不可撤销。`,
    hideCancel: false,
    onOk: () => emit("bulk-delete", ids)
  });
};
const formatTime = (value: number | string | null | undefined) => {
  if (value === null || value === undefined || value === "") return "—";
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
  }).format(date);
};
const statusText = (status: string) => ({ active: "进行中", completed: "已完成", failed: "下载失败" }[status] || status);
const statusColor = (status: string) => ({ active: "arcoblue", completed: "green", failed: "red" }[status] || "gray");
</script>

<style scoped>
.download-table {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.table-actions {
  display: flex;
  justify-content: flex-end;
  padding-bottom: 12px;
}
.pagination-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  justify-content: flex-end;
  padding: 12px 0 4px;
  background: var(--color-bg-2, #fff);
}
</style>
