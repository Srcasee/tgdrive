<template>
  <div class="snow-page">
    <a-card title="下载记录">
      <a-tabs v-model:active-key="status" @change="onStatusChange">
        <a-tab-pane key="active" title="进行中" />
        <a-tab-pane key="completed" title="已完成" />
        <a-tab-pane key="failed" title="下载失败" />
      </a-tabs>
      <DownloadTable
        :rows="rows"
        :status="status"
        :page="page"
        :size="size"
        :total="total"
        @page-change="changePage"
        @bulk-delete="bulkDelete"
      />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Message } from "@arco-design/web-vue";
import DownloadTable from "./table.vue";
import { getDownloadRecordsAPI, bulkDeleteDownloadsAPI, type DownloadStatus } from "@/api/modules/tgdrive";

const status = ref<DownloadStatus>("active");
const rows = ref<any[]>([]);
const page = ref(1);
const size = 50;
const total = ref(0);

const load = async () => {
  const response = await getDownloadRecordsAPI({ status: status.value, page: page.value, size });
  const payload = response.data || {};
  rows.value = payload.items || [];
  total.value = payload.total || 0;
};
const onStatusChange = () => {
  page.value = 1;
  load();
};
const changePage = (nextPage: number) => {
  page.value = nextPage;
  load();
};
const bulkDelete = async (ids: number[]) => {
  await bulkDeleteDownloadsAPI(ids);
  Message.success("已删除选中的下载记录");
  await load();
};
onMounted(load);
</script>

<style scoped>
.snow-page :deep(.arco-card-body) {
  min-height: calc(100vh - 180px);
}
</style>
