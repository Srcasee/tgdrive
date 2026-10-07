<template>
  <div class="snow-page">
    <a-card title="下载管理">
      <a-tabs v-model:active-key="tab">
        <a-tab-pane key="active" title="活动下载"><DownloadTable :rows="active" :active="true" @remove="remove" /></a-tab-pane>
        <a-tab-pane key="history" title="历史记录"><DownloadTable :rows="history" :active="false" @remove="remove" /></a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue";
import DownloadTable from "./table.vue";
import { getActiveDownloadsAPI, getDownloadHistoryAPI, deleteDownloadAPI } from "@/api/modules/tgdrive";
const tab=ref("active"),active=ref<any[]>([]),history=ref<any[]>([]);
const load=async()=>{active.value=(await getActiveDownloadsAPI()).data||[];history.value=(await getDownloadHistoryAPI()).data||[]}; const remove=async(id:number)=>{await deleteDownloadAPI(id);await load()};load();
</script>
