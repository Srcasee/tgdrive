<template>
  <div class="snow-page">
    <a-card title="群组/频道管理" :bordered="false">
      <a-empty v-if="!loading && accounts.length === 0" description="暂无已启用账号" />

      <template v-else>
        <div class="account-switcher">
          <a-button
            v-for="(account, index) in accounts"
            :key="account.account_id"
            class="account-button"
            :class="[accountColorClass(index), { active: selectedAccountId === account.account_id }]"
            @click="selectedAccountId = account.account_id"
          >
            {{ displayNickname(account) }}
          </a-button>
        </div>

        <a-card v-if="selectedAccount" class="channel-card" :bordered="true">
          <template #title>{{ displayNickname(selectedAccount) }}</template>

          <a-table
            :data="selectedAccount.channels"
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
      </template>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
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
  nickname: string | null;
  username: string | null;
  channels: ChannelRow[];
};

const accounts = ref<AccountGroup[]>([]);
const selectedAccountId = ref<number | null>(null);
const loading = ref(false);

const selectedAccount = computed(() =>
  accounts.value.find(account => account.account_id === selectedAccountId.value) || null
);

const displayNickname = (account: AccountGroup) => {
  const nickname = account.nickname?.trim();
  return nickname || (account.username?.trim() ? `@${account.username.trim()}` : `账号 #${account.account_id}`);
};

const accountColorClass = (index: number) => `account-color-${index % 8}`;

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

    if (!accounts.value.some(account => account.account_id === selectedAccountId.value)) {
      selectedAccountId.value = accounts.value[0]?.account_id ?? null;
    }
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
.account-switcher {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.account-button {
  border: 1px solid transparent;
  color: #fff;
  font-weight: 600;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.account-button:hover {
  opacity: 0.88;
  transform: translateY(-1px);
}

.account-button.active {
  box-shadow: 0 0 0 2px var(--color-bg-2), 0 0 0 4px currentColor;
}

.account-color-0 { background: #165dff; }
.account-color-1 { background: #00b42a; }
.account-color-2 { background: #ff7d00; }
.account-color-3 { background: #722ed1; }
.account-color-4 { background: #14c9c9; }
.account-color-5 { background: #f53f3f; }
.account-color-6 { background: #d91ad9; }
.account-color-7 { background: #86909c; }

.channel-card {
  width: 100%;
}
</style>