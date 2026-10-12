<template>
  <div class="container-page">
    <a-row :gutter="12" align="center" class="bottom-gap">
      <a-col :flex="1">
        <a-input v-model="keyword" allow-clear placeholder="搜索资源文件名" @press-enter="search" />
      </a-col>
      <a-col>
        <a-space>
          <input v-model="expiresAt" class="expiration-input" type="datetime-local" aria-label="分享链接到期时间" />
          <a-button type="primary" @click="search">搜索</a-button>
          <a-button @click="getList()">刷新</a-button>
        </a-space>
      </a-col>
    </a-row>
    <div class="share-hint">分享有效期：留空为永久；填写未来时间后，新建或刷新分享链接时应用。刷新会立即使旧链接失效。</div>
    <a-table
      row-key="id"
      size="small"
      :bordered="{ cell: true }"
      :loading="loading"
      :data="list"
      :pagination="{ current: page, pageSize: pageSize, total, showTotal: true, showPageSize: true }"
      @page-change="onPageChange"
      @page-size-change="onPageSizeChange"
    >
      <template #columns>
        <a-table-column title="资源 ID" data-index="id" :width="90" />
        <a-table-column title="文件名" data-index="filename" :width="280">
          <template #cell="{ record }"><span class="filename">{{ record.filename }}</span></template>
        </a-table-column>
        <a-table-column title="大小" data-index="size" :width="120">
          <template #cell="{ record }">{{ formatSize(record.size) }}</template>
        </a-table-column>
        <a-table-column title="来源" data-index="source_count" :width="90" />
        <a-table-column title="分享链接">
          <template #cell="{ record }">
            <div v-if="activeShare(record)" class="share-record">
              <a-link :href="shareUrl(activeShare(record))" target="_blank">{{ shareUrl(activeShare(record)) }}</a-link>
              <a-tag v-if="isExpired(activeShare(record))" color="red">已过期</a-tag>
              <a-tag v-else-if="activeShare(record)?.expires_at" color="arcoblue">有效至 {{ formatDate(activeShare(record).expires_at) }}</a-tag>
              <a-tag v-else color="green">永久有效</a-tag>
            </div>
            <span v-else class="muted">尚未创建分享链接</span>
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="250" fixed="right">
          <template #cell="{ record }">
            <a-space wrap>
              <a-button size="mini" type="primary" :loading="busyId === record.id" @click="createOrRotateShare(record)">
                {{ activeShare(record) ? "刷新链接" : "创建链接" }}
              </a-button>
              <a-button v-if="activeShare(record)" size="mini" @click="copyShare(record)">复制</a-button>
              <a-button v-if="isAdmin && activeShare(record)" size="mini" status="danger" @click="revokeShare(record)">管理员撤销</a-button>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { Message } from "@arco-design/web-vue";
import { createShareAPI, deleteShareAPI, getResourcesAPI, searchResourcesAPI } from "@/api/modules/tgdrive";

interface ShareRecord {
  id: number;
  token: string;
  url: string;
  created_at: number;
  expires_at: number | null;
}
interface ResourceRecord {
  id: number;
  filename: string;
  size: number;
  source_count: number;
  shares?: ShareRecord[];
}
const loading = ref(false);
const busyId = ref<number | null>(null);
const list = ref<ResourceRecord[]>([]);
const keyword = ref("");
const expiresAt = ref("");
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const scope = ref<{ account_id?: number; chat_id?: number; topic_id?: number }>({});
const isAdmin = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem("user-info") || "{}");
    return user?.role === "admin" || user?.user?.role === "admin";
  } catch {
    return false;
  }
});

const activeShare = (resource: ResourceRecord) => resource.shares?.[0];
const shareUrl = (share?: ShareRecord) => share ? new URL(share.url, window.location.origin).toString() : "";
const isExpired = (share?: ShareRecord) => Boolean(share && share.expires_at !== null && share.expires_at * 1000 <= Date.now());
const formatDate = (seconds?: number | null) => seconds ? new Date(seconds * 1000).toLocaleString() : "";
const formatSize = (size: number) => {
  if (!Number.isFinite(size) || size < 0) return "-";
  if (size < 1024) return `${size} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = size;
  let unit = "B";
  for (const next of units) {
    value /= 1024;
    unit = next;
    if (value < 1024) break;
  }
  return `${value.toFixed(1)} ${unit}`;
};

const getList = async (treePath?: any[]) => {
  if (treePath?.length) {
    const node = treePath[treePath.length - 1];
    scope.value = {
      account_id: node.account_id,
      chat_id: node.chat_id,
      topic_id: node.topic_id
    };
    page.value = 1;
  } else if (treePath && treePath.length === 0) {
    scope.value = {};
  }
  loading.value = true;
  try {
    const response = keyword.value.trim()
      ? await searchResourcesAPI({ q: keyword.value.trim(), limit: 200, ...scope.value })
      : await getResourcesAPI({ page: page.value, size: pageSize.value, sort: "id", order: "desc", ...scope.value });
    const payload = response.data?.data;
    if (keyword.value.trim()) {
      const rows = Array.isArray(payload) ? payload : [];
      list.value = rows;
      total.value = rows.length;
    } else {
      list.value = payload?.items || [];
      total.value = payload?.total || 0;
    }
  } catch {
    Message.error("加载资源列表失败，请检查登录状态或网络连接");
  } finally {
    loading.value = false;
  }
};
const search = () => {
  page.value = 1;
  getList();
};
const onPageChange = (nextPage: number) => {
  page.value = nextPage;
  getList();
};
const onPageSizeChange = (nextSize: number) => {
  pageSize.value = nextSize;
  page.value = 1;
  getList();
};
const createOrRotateShare = async (resource: ResourceRecord) => {
  if (activeShare(resource) && !window.confirm("刷新链接会立即使旧链接失效，确定继续吗？")) return;
  let expiration: string | null = null;
  if (expiresAt.value) {
    const date = new Date(expiresAt.value);
    if (Number.isNaN(date.getTime()) || date.getTime() <= Date.now()) {
      Message.warning("到期时间必须是未来时间");
      return;
    }
    expiration = date.toISOString();
  }
  busyId.value = resource.id;
  try {
    const response = await createShareAPI(resource.id, expiration);
    if (response.data?.success === false) throw new Error(response.data.message || "创建分享失败");
    Message.success("分享链接已创建");
    await getList();
    const url = response.data?.url || response.data?.data?.url;
    if (url) await navigator.clipboard?.writeText(new URL(url, window.location.origin).toString());
  } catch (error: any) {
    Message.error(error?.message || "创建分享链接失败");
  } finally {
    busyId.value = null;
  }
};
const copyShare = async (resource: ResourceRecord) => {
  const share = activeShare(resource);
  if (!share) return;
  try {
    await navigator.clipboard.writeText(shareUrl(share));
    Message.success("链接已复制");
  } catch {
    Message.error("复制失败，请手动复制链接");
  }
};
const revokeShare = async (resource: ResourceRecord) => {
  const share = activeShare(resource);
  if (!share || !window.confirm("确定撤销此分享链接吗？撤销后链接将立即失效。")) return;
  try {
    await deleteShareAPI(share.id);
    Message.success("分享链接已撤销");
    await getList();
  } catch {
    Message.error("撤销失败，请确认当前账号具有管理员权限");
  }
};

defineExpose({ getList });
getList();
</script>

<style lang="scss" scoped>
.container-page { box-sizing: border-box; height: 100%; padding: $padding; overflow: auto; }
.bottom-gap { margin-bottom: $padding; }
.expiration-input { min-height: 30px; max-width: 220px; padding: 0 8px; border: 1px solid var(--color-border-2); border-radius: 4px; color: var(--color-text-1); background: var(--color-bg-2); }
.share-hint { margin: -4px 0 12px; color: var(--color-text-3); font-size: 12px; }
.filename { overflow-wrap: anywhere; font-weight: 500; }
.share-record { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.muted { color: var(--color-text-3); }
</style>
