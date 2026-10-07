<template>
  <div class="snow-page">
    <a-grid :cols="{ xs: 1, sm: 2, md: 4 }" :col-gap="16" :row-gap="16">
      <a-grid-item v-for="item in cards" :key="item.title">
        <a-card :title="item.title"><div class="value">{{ item.value }}</div></a-card>
      </a-grid-item>
    </a-grid>
    <a-card title="Telegram 运行控制" class="mt">
      <a-space>
        <a-button type="primary" :loading="loading" @click="run(reconnectTelegramAPI)">重新连接 Telegram</a-button>
        <a-button :loading="loading" @click="run(reconcileTelegramAPI)">重新同步运行状态</a-button>
      </a-space>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { getAccountsAPI, getSourcesAPI, getCategoriesAPI, getActiveDownloadsAPI, reconnectTelegramAPI, reconcileTelegramAPI } from "@/api/modules/tgdrive";

const loading = ref(false);
const cards = ref([
  { title: "Telegram 账号", value: 0 },
  { title: "启用来源", value: 0 },
  { title: "资源分类", value: 0 },
  { title: "活动下载", value: 0 }
]);
const load = async () => {
  const [accounts, sources, categories, downloads] = await Promise.all([
    getAccountsAPI(), getSourcesAPI(), getCategoriesAPI(), getActiveDownloadsAPI()
  ]);
  cards.value[0].value = accounts.data?.length ?? 0;
  cards.value[1].value = sources.data?.length ?? 0;
  cards.value[2].value = categories.data?.length ?? 0;
  cards.value[3].value = downloads.data?.length ?? 0;
};
const run = async (fn: () => Promise<unknown>) => {
  loading.value = true;
  try { await fn(); await load(); } finally { loading.value = false; }
};
load();
</script>

<style scoped>
.mt { margin-top: 16px; }
.value { font-size: 28px; font-weight: 600; }
</style>
