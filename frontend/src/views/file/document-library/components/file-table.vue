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
              <a-tag v-else-if="activeShare(record)?.expires_at" color="arcoblue">有效至 {{ formatDate(activeShare(record)?.expires_at) }}</a-tag>
              <a-tag v-else color="green">永久有效</a-tag>
            </div>
            <span v-else class="muted">尚未创建分享链接</span>
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="250" fixed="right">
          <template #cell="{ record }">
            <a-space wrap>
              <a-button size="mini" type="primary" :loading="busyId === record.id" @click="createOrRotateShare(record)">
                {{ activeShare(record) ? "刷新分享" : "分享" }}
              </a-button>
              <a-button v-if="activeShare(record)" size="mini" @click="openShareDetails(record)">资源详情</a-button>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>
    <a-modal v-model:visible="shareModalVisible" title="资源详情" :footer="false">
      <div v-if="selectedResource" class="detail-panel">
        <div><strong>文件名：</strong>{{ selectedResource.filename }}</div>
        <div><strong>大小：</strong>{{ formatSize(selectedResource.size) }}</div>
        <div v-if="selectedShare" class="detail-share">
          <div><strong>分享链接：</strong></div>
          <a-input :model-value="selectedShareUrl" readonly />
          <div class="detail-meta">
            <a-tag v-if="isExpired(selectedShare)" color="red">已过期</a-tag>
            <a-tag v-else-if="selectedShare.expires_at" color="arcoblue">有效至 {{ formatDate(selectedShare.expires_at) }}</a-tag>
            <a-tag v-else color="green">永久有效</a-tag>
          </div>
          <a-space wrap>
            <a-button type="primary" @click="copySelectedShare">复制完整链接</a-button>
            <a-button v-if="isAdmin" status="danger" @click="revokeShare(selectedResource)">删除</a-button>
          </a-space>
        </div>
        <div v-else class="muted">尚未创建分享链接</div>
      </div>
    </a-modal>
    <a-modal v-model:visible="createdShareModalVisible" title="分享链接已创建" :footer="false">
      <div class="detail-panel">
        <div><strong>完整分享链接：</strong></div>
        <a-input :model-value="createdShareUrl" readonly />
        <a-space wrap>
          <a-button type="primary" @click="copyCreatedShare">复制完整链接</a-button>
          <a-button @click="createdShareModalVisible = false">关闭</a-button>
        </a-space>
      </div>
    </a-modal>
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
const shareModalVisible = ref(false);
const createdShareModalVisible = ref(false);
const createdShareUrl = ref("");
const selectedResource = ref<ResourceRecord | null>(null);
const selectedShare = computed(() => selectedResource.value?.shares?.[0]);
const selectedShareUrl = computed(() => shareUrl(selectedShare.value));
const scope = ref<{ account_id?: number; chat_id?: number; topic_id?: number }>({});
const isAdmin = computed(() => {
  try {
    const userInfo = JSON.parse(localStorage.getItem("user-info") || "{}");
    return (
      userInfo?.account?.roles?.includes("admin") ||
      userInfo?.account?.user?.role === "admin" ||
      userInfo?.role === "admin" ||
      userInfo?.user?.role === "admin"
    );
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
const openShareDetails = (resource: ResourceRecord) => {
  selectedResource.value = resource;
  shareModalVisible.value = true;
};
const copyText = async (value: string) => {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) throw new Error("浏览器拒绝了复制操作");
};
const copySelectedShare = async () => {
  if (!selectedShareUrl.value) return;
  try {
    await copyText(selectedShareUrl.value);
    Message.success("完整分享链接已复制");
  } catch {
    Message.error("复制失败，请手动选择完整链接");
  }
};
const copyCreatedShare = async () => {
  if (!createdShareUrl.value) return;
  try {
    await copyText(createdShareUrl.value);
    Message.success("完整分享链接已复制");
  } catch {
    Message.error("复制失败，请手动选择完整链接");
  }
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
    const payload = response.data?.data ?? response.data;
    const rawUrl = payload?.url || activeShare(resource)?.url;
    if (!rawUrl) throw new Error("链接已创建，但服务器未返回分享地址");
    const parsedUrl = new URL(rawUrl, window.location.origin);
    createdShareUrl.value = new URL(parsedUrl.pathname + parsedUrl.search, window.location.origin).toString();
    createdShareModalVisible.value = true;
    await getList();
    const refreshedResource = list.value.find(item => item.id === resource.id);
    if (refreshedResource) {
      selectedResource.value = refreshedResource;
    }
    try {
      await copyText(createdShareUrl.value);
      Message.success("分享链接已创建，完整链接已复制");
    } catch {
      Message.info("分享链接已创建，请在弹窗中点击“复制完整链接”");
    }
  } catch (error: any) {
    Message.error(error?.message || "创建分享链接失败");
  } finally {
    busyId.value = null;
  }
};
const revokeShare = async (resource: ResourceRecord) => {
  const share = activeShare(resource);
  if (!share || !window.confirm("确定撤销此分享链接吗？撤销后链接将立即失效。")) return;
  try {
    await deleteShareAPI(share.id);
    Message.success("分享链接已删除");
    shareModalVisible.value = false;
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
.detail-panel { display: flex; flex-direction: column; gap: 12px; overflow-wrap: anywhere; }
.detail-share { display: flex; flex-direction: column; gap: 8px; }
.detail-meta { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
