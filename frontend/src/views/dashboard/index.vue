<template>
  <div class="snow-page">
    <a-grid :cols="{ xs: 1, sm: 2, md: 4 }" :col-gap="16" :row-gap="16">
      <a-grid-item v-for="item in cards" :key="item.title">
        <a-card :title="item.title"><div class="value">{{ item.value }}</div></a-card>
      </a-grid-item>
    </a-grid>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { getAccountsAPI, getDialogsAPI, getCategoriesAPI, getDownloadRecordsAPI } from "@/api/modules/tgdrive";

const cards = ref([
  { title: "Telegram 账号", value: 0 },
  { title: "启用来源", value: 0 },
  { title: "资源分类", value: 0 },
  { title: "进行中", value: 0 }
]);
const load = async () => {
  const [accounts, dialogs, categories, downloads] = await Promise.all([
    getAccountsAPI(), getDialogsAPI(), getCategoriesAPI(), getDownloadRecordsAPI({ status: "active", page: 1, size: 1 })
  ]);
  cards.value[0].value = accounts.data?.length ?? 0;
  cards.value[1].value = dialogs.data?.flatMap((account: { channels?: { source_enabled?: boolean }[] }) => account.channels ?? [])
    .filter((channel: { source_enabled?: boolean }) => channel.source_enabled).length ?? 0;
  cards.value[2].value = categories.data?.length ?? 0;
  cards.value[3].value = downloads.data?.total ?? 0;
};
load();
</script>

<style scoped>
.value { font-size: 28px; font-weight: 600; }
</style>
