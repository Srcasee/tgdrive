<template>
  <div class="snow-page">
    <a-card title="群组/频道管理" :bordered="false">
      <a-empty v-if="!loading && accounts.length === 0" description="暂无已启用账号" />

      <div v-else class="account-list">
        <a-card
          v-for="account in accounts"
          :key="account.account_id"
          class="account-card"
          :bordered="true"
        >
          <template #title>
            <div class="account-title">
              <span class="account-label">用户名</span>
              <span class="account-username">{{ displayUsername(account) }}</span>
            </div>
          </template>

          <a-table
            :data="account.channels"
            :loading="loading"
            row-key="row_key"
            :bordered="{ cell: true }"
            :scroll="{ x: '100%' }"
            :pagination="{ pageSize: 20, showPageSize: false }"
          >
            <template #columns>
              <a-table-column title="Chat ID" data-index="telegram_chat_id" :width="180" />
              <a-table-column title="名称" data-index="name" :width="280" ellipsis tooltip />
              <a-table-column title="用户名" data-index="username" :width="220" ellipsis tooltip>
                <template #cell="{ record }">
                  {{ record.username ? `@${record.username}` : "-" }}
                </template>
              </a-table-column>
              <a-table-column title="状态" :width="100" align="center">
                <template #cell="{ record }">
                  <a-switch
                    v-model="record.source_enabled"
                    :loading="record.toggling"
                    @change="toggle(record)"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { getDialogsAPI, setDialogEnabledAPI } from "@/api/modules/tgdrive";

type ChannelRow = {
  account_id: number;
  telegram_chat_id: number;
  name: string | null;
  username: string | null;
  source_enabled: boolean;
  toggling: boolean;
  row_key: string;
};

type AccountGroup = {
  account_id: number;
  name: string | null;
  username: string | null;
  channels: ChannelRow[];
};

const accounts = ref<AccountGroup[]>([]);
const loading = ref(false);

const displayUsername = (account: AccountGroup) => {
  const username = account.username?.trim();
  return username ? `@${username}` : "-";
};

const load = async () => {
  loading.value = true;
  try {
    const data = (await getDialogsAPI()).data || [];
    accounts.value = data.map((account: any) => ({
      ...account,
      channels: (account.channels || [])
        .filter((item: any) => item.entity_type === "Channel")
        .map((item: any) => ({
          ...item,
          source_enabled: Boolean(item.source_enabled),
          toggling: false,
          row_key: `${item.account_id}:${item.telegram_chat_id}`
        }))
    }));
  } finally {
    loading.value = false;
  }
};

const toggle = async (row: ChannelRow) => {
  row.toggling = true;
  try {
    await setDialogEnabledAPI(row.account_id, row.telegram_chat_id, row.source_enabled);
  } catch (error) {
    row.source_enabled = !row.source_enabled;
    throw error;
  } finally {
    row.toggling = false;
  }
};

load();
</script>

<style scoped>
.account-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account-card {
  width: 100%;
}

.account-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.account-label {
  color: var(--color-text-3);
  font-weight: 400;
}

.account-username {
  font-weight: 600;
}
</style>
