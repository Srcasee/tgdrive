<template>
  <div class="snow-page">
    <a-card :bordered="false">
      <template #title>群组/频道管理</template>
      <template #extra>
        <a-button type="primary" :loading="refreshing" @click="refresh">
          刷新
        </a-button>
      </template>
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
              <a-table-column title="类型" :width="100" align="center">
                <template #cell="{ record }">
                  {{ record.is_group ? "群组" : "频道" }}
                </template>
              </a-table-column>
              <a-table-column title="用户名" data-index="username" :width="220" ellipsis tooltip>
                <template #cell="{ record }">
                  {{ record.username ? `@${record.username}` : "-" }}
                </template>
              </a-table-column>
              <a-table-column title="状态" :width="100" align="center">
                <template #cell="{ record }">
                  <a-switch
                    v-model="record.source_enabled"
                    :disabled="!record.source_id"
                    :loading="record.toggling"
                    @change="toggle(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="180" align="center">
                <template #cell="{ record }">
                  <a-space>
                    <a-button
                      size="small"
                      type="primary"
                      :disabled="Boolean(record.source_id)"
                      :loading="record.creating"
                      @click="createSource(record)"
                    >
                      新增
                    </a-button>
                    <a-popconfirm
                      v-if="record.source_id"
                      content="确定删除这个 Source 条目吗？删除后该 Source 将不再参与扫描。"
                      @ok="removeSource(record)"
                    >
                      <a-button size="small" status="danger" :loading="record.deleting">删除</a-button>
                    </a-popconfirm>
                    <a-button v-else size="small" status="danger" disabled>删除</a-button>
                  </a-space>
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
import {
  getDialogsAPI,
  refreshDialogsAPI,
  createSourceAPI,
  setDialogSourceEnabledAPI,
  deleteSourceAPI
} from "@/api/modules/tgdrive";

type ChannelRow = {
  account_id: number;
  telegram_chat_id: number;
  name: string | null;
  username: string | null;
  is_group: boolean;
  source_enabled: boolean;
  toggling: boolean;
  creating: boolean;
  deleting: boolean;
  row_key: string;
  source_id: number | null;
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
const refreshing = ref(false);

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
          creating: false,
          deleting: false,
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

const refresh = async () => {
  refreshing.value = true;
  try {
    await refreshDialogsAPI();
    await new Promise(resolve => setTimeout(resolve, 800));
    await load();
  } finally {
    refreshing.value = false;
  }
};

const createSource = async (row: ChannelRow) => {
  if (row.source_id) return;
  row.creating = true;
  try {
    await createSourceAPI(row.account_id, row.telegram_chat_id);
    await load();
  } finally {
    row.creating = false;
  }
};

const removeSource = async (row: ChannelRow) => {
  if (!row.source_id) return;
  row.deleting = true;
  try {
    await deleteSourceAPI(row.source_id);
    await load();
  } finally {
    row.deleting = false;
  }
};

const toggle = async (row: ChannelRow) => {
  if (!row.source_id) {
    row.source_enabled = false;
    return;
  }
  row.toggling = true;
  try {
    await setDialogSourceEnabledAPI(row.account_id, row.telegram_chat_id, row.source_enabled);
    await load();
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
