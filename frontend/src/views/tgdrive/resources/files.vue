<template>
  <div class="snow-page">
    <div ref="catalogLayout" class="catalog-layout">
      <aside class="tree-panel" :style="{ width: treeWidth + 'px', flexBasis: treeWidth + 'px' }">
        <div class="panel-title">资源归属</div>
        <a-divider margin="0" />
        <div class="tree-content">
          <a-input v-model="treeKeyword" allow-clear placeholder="搜索账号、群组、话题" class="tree-search">
            <template #prefix><icon-search /></template>
          </a-input>
          <a-spin :loading="treeLoading" class="tree-spin">
            <a-tree :data="visibleTree" :default-expand-all="true" :show-line="true" :selected-keys="selectedTreeKeys" @select="onTreeSelect">
              <template #title="{ title }"><span class="tree-node-title">{{ title }}</span></template>
              <template #icon="{ isLeaf, expanded }">
                <s-svg-icon v-if="!isLeaf && !expanded" name="folder-close" :size="16" />
                <s-svg-icon v-else-if="!isLeaf" name="folder-open" :size="16" />
                <s-svg-icon v-else name="txt" :size="16" />
              </template>
            </a-tree>
          </a-spin>
        </div>
      </aside>
      <div class="tree-resizer" role="separator" aria-orientation="vertical" aria-label="调整资源归属面板宽度" @pointerdown="startResize"></div>
      <section class="resource-panel">
        <div class="panel-title resource-panel-title">
          <a-breadcrumb>
            <a-breadcrumb-item v-for="item in breadcrumb" :key="item.key">{{ item.title }}</a-breadcrumb-item>
            <a-breadcrumb-item v-if="!breadcrumb.length">全部资源</a-breadcrumb-item>
          </a-breadcrumb>
          <div class="header-actions">
            <a-button @click="resetTreeSelection">全部资源</a-button>
            <a-input-search v-model="keyword" placeholder="搜索文件名" class="resource-search" @search="onSearch" />
          </div>
        </div>
        <a-divider margin="0" />
        <div class="resource-content">
          <div v-if="batchSelectionEnabled" class="batch-toolbar">
            <a-checkbox :model-value="currentPageAllSelected" :indeterminate="currentPageSomeSelected" @change="toggleCurrentPageSelection">选择当前页</a-checkbox>
            <span>已选 {{ selectedResources.size }} 项 · {{ formatSize(selectedTotalSize) }}</span>
            <a-button size="small" :disabled="selectedResources.size === 0 || batchRunning" @click="clearSelection">清空选择</a-button>
            <a-button size="small" type="primary" :disabled="selectedResources.size === 0 || batchRunning" @click="startBatchDownload">批量下载（并发 8）</a-button>
            <a-button v-if="batchRunning" size="small" status="warning" @click="stopBatchDownload">停止后续任务</a-button>
            <span v-if="batchStatus" class="batch-status">{{ batchStatus }}</span>
          </div>
          <a-table
            :data="rows"
            :loading="loading"
            :pagination="pagination"
            :scroll="{ y: '100%' }"
            row-key="id"
            size="small"
            @page-change="onPageChange"
            @page-size-change="onPageSizeChange"
          >
            <template #columns>
              <a-table-column v-if="batchSelectionEnabled" title="选择" :width="72" align="center">
                <template #cell="{ record }">
                  <a-checkbox :model-value="selectedResources.has(String(record.id))" :disabled="batchRunning" @change="(checked: boolean) => toggleResourceSelection(record, checked)" />
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="180">
                <template #cell="{ record }">
                  <a-space>
                    <a-button size="small" @click="detail(record)">查看</a-button>
                    <a-button size="small" type="primary" @click="downloadResource(record)">下载</a-button>
                    <!-- Manual category assignment is disabled; original control retained as a comment.
                    <a-button size="small" @click="setCategories(record)">分类</a-button>
                    -->
                  </a-space>
                </template>
              </a-table-column>
              <a-table-column
                v-for="item in visibleDetailColumns"
                :key="item.key"
                :title="item.label"
                :data-index="item.key"
                :width="columnWidth(item.key)"
              >
                <template #cell="{ record }">{{ formatCell(record._detailValues?.[item.key] ?? record[item.key]) }}</template>
              </a-table-column>
              <a-table-column title="来源账号" :width="180">
                <template #cell="{ record }">
                  <a-space wrap>
                    <a-tag v-for="account in sourceAccounts(record)" :key="account.id" size="small">
                      {{ account.name }}
                    </a-tag>
                    <span v-if="!sourceAccounts(record).length">—</span>
                  </a-space>
                </template>
              </a-table-column>
              <a-table-column title="分享操作" :width="180">
                <template #cell="{ record }">
                  <a-space>
                    <a-button size="small" @click="share(record)">创建</a-button>
                    <a-button v-for="shareItem in (record.shares || [])" :key="shareItem.id" size="small" status="danger" @click="removeShare(shareItem)">删除 {{ shareItem.id }}</a-button>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
      </section>
    </div>
    <a-modal v-model:visible="detailOpen" title="资源详情" hide-cancel @ok="detailOpen=false" :width="720">
      <a-space direction="vertical" fill size="medium">
        <a-checkbox :model-value="allDetailsVisible" :indeterminate="someDetailsVisible" @change="toggleAllDetails">列表全部显示</a-checkbox>
        <a-divider margin="0" />
        <div v-for="item in detailRows" :key="item.key" class="detail-row">
          <a-checkbox :model-value="isDetailVisible(item.key)" @change="setDetailVisibility(item.key, $event)">列表显示：{{ item.label }}</a-checkbox>
          <div class="detail-value">{{ item.value }}</div>
        </div>
      </a-space>
    </a-modal>
    <!-- Manual category assignment is disabled; original dialog retained as a comment.
    <a-modal v-model:visible="categoryOpen" title="设置分类" @ok="saveCategories">
      <a-input v-model="categoryText" placeholder="分类 ID，逗号分隔" />
    </a-modal>
    -->
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import {
  getResourcesAPI, getResourceAPI, searchResourcesAPI, getResourceTreeAPI,
  createShareAPI, deleteShareAPI
} from "@/api/modules/tgdrive";

type TreeNode = {
  key: string;
  title: string;
  account_id?: number;
  chat_id?: number;
  topic_id?: number;
  isLeaf?: boolean;
  children?: TreeNode[];
};

const catalogLayout = ref<HTMLElement | null>(null);
const treeWidth = ref(280);
const resizing = ref(false);

const resizeTree = (event: PointerEvent) => {
  if (!resizing.value || !catalogLayout.value) return;
  const bounds = catalogLayout.value.getBoundingClientRect();
  treeWidth.value = Math.max(200, Math.min(event.clientX - bounds.left, bounds.width * 0.5));
};
const stopResize = () => {
  resizing.value = false;
  document.removeEventListener("pointermove", resizeTree);
  document.removeEventListener("pointerup", stopResize);
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
};
const startResize = (event: PointerEvent) => {
  if (window.matchMedia("(max-width: 768px)").matches) return;
  event.preventDefault();
  resizing.value = true;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
  document.addEventListener("pointermove", resizeTree);
  document.addEventListener("pointerup", stopResize);
};
onBeforeUnmount(stopResize);

const rows = ref<any[]>([]);
const loading = ref(false);
const treeLoading = ref(false);
const keyword = ref("");
const treeKeyword = ref("");
const accountId = ref<number>();
const chatId = ref<number>();
const topicId = ref<number>();
const treeData = ref<TreeNode[]>([]);
const selectedTreeKeys = ref<string[]>([]);
const breadcrumb = ref<TreeNode[]>([]);
const detailOpen = ref(false);
const selectedResources = ref(new Map<string, any>());
const batchSelectionEnabled = computed(() => accountId.value != null && chatId.value != null);
const currentPageAllSelected = computed(() => rows.value.length > 0 && rows.value.every((record: any) => selectedResources.value.has(String(record.id))));
const currentPageSomeSelected = computed(() => rows.value.some((record: any) => selectedResources.value.has(String(record.id))) && !currentPageAllSelected.value);
const selectedTotalSize = computed(() => [...selectedResources.value.values()].reduce((total: number, record: any) => total + (Number(record.size) || 0), 0));
const batchRunning = ref(false);
const batchStopRequested = ref(false);
const batchStatus = ref("");
// Manual category assignment state is disabled; retained as comments.
// const categoryOpen = ref(false);
// const currentId = ref<number>();
// const categoryText = ref("");
type DetailItem = { key: string; label: string; value: string; visible: boolean };
const detailRows = ref<DetailItem[]>([]);
const fieldVisibility = ref<Record<string, boolean>>({});
const defaultVisibleDetailKeys = new Set(["filename", "size", "mime_type"]);
const isDetailVisible = (key: string) => fieldVisibility.value[key] ?? defaultVisibleDetailKeys.has(key);
const visibleDetailColumns = computed(() => detailRows.value.filter(item => isDetailVisible(item.key)));
const allDetailsVisible = computed(() => detailRows.value.length > 0 && detailRows.value.every(item => isDetailVisible(item.key)));
const someDetailsVisible = computed(() => detailRows.value.some(item => isDetailVisible(item.key)) && !allDetailsVisible.value);
const setDetailVisibility = (key: string, visible: boolean) => {
  fieldVisibility.value[key] = visible;
  const item = detailRows.value.find(row => row.key === key);
  if (item) item.visible = visible;
};
const toggleAllDetails = (visible: boolean) => detailRows.value.forEach(item => {
  fieldVisibility.value[item.key] = visible;
  item.visible = visible;
});
const sourceAccounts = (record: any) => {
  const sources = Array.isArray(record.sources) ? record.sources : [];
  const unique = new Map<number | string, { id: number | string; name: string }>();
  for (const source of sources) {
    const id = source.account_id ?? "unknown";
    const name = source.account_name || (source.account_id != null ? `账号 ${source.account_id}` : "未知账号");
    if (!unique.has(id)) unique.set(id, { id, name });
  }
  return [...unique.values()];
};
const formatCell = (value: unknown) => {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
};
const columnWidth = (key: string) => ["id", "size", "source_count", "status"].includes(key) ? 110 : undefined;
const pagination = ref({
  current: 1,
  pageSize: 15,
  total: 0,
  showPageSize: true,
  pageSizeOptions: [15, 30, 50, 100],
  showTotal: true
});

const filterTree = (nodes: TreeNode[], query: string): TreeNode[] => {
  if (!query) return nodes;
  const q = query.toLowerCase();
  return nodes.reduce<TreeNode[]>((result, node) => {
    const children = filterTree(node.children || [], query);
    if (node.title.toLowerCase().includes(q) || children.length) result.push({ ...node, children });
    return result;
  }, []);
};
const visibleTree = computed(() => filterTree(treeData.value, treeKeyword.value.trim()));

const findPath = (nodes: TreeNode[], key: string, parents: TreeNode[] = []): TreeNode[] | undefined => {
  for (const node of nodes) {
    const path = [...parents, node];
    if (node.key === key) return path;
    const found = findPath(node.children || [], key, path);
    if (found) return found;
  }
  return undefined;
};

const load = async () => {
  loading.value = true;
  try {
    const params = {
      account_id: accountId.value,
      chat_id: chatId.value,
      topic_id: topicId.value
    };
    if (keyword.value.trim()) {
      const response = await searchResourcesAPI({ q: keyword.value.trim(), ...params, limit: 200 });
      const payload = response.data?.data;
      rows.value = Array.isArray(payload?.items) ? payload.items : Array.isArray(payload) ? payload : [];
      pagination.value.total = rows.value.length;
      await hydrateRowDetails();
    } else {
      const response = await getResourcesAPI({
        page: pagination.value.current,
        size: pagination.value.pageSize,
        ...params
      });
      const payload = response.data?.data;
      rows.value = Array.isArray(payload?.items) ? payload.items : Array.isArray(payload) ? payload : [];
      pagination.value.total = Number(payload?.total ?? rows.value.length);
      await hydrateRowDetails();
    }
  } finally {
    loading.value = false;
  }
};

const loadTree = async () => {
  treeLoading.value = true;
  try {
    const response = await getResourceTreeAPI();
    treeData.value = Array.isArray(response.data?.data) ? response.data.data : [];
  } finally {
    treeLoading.value = false;
  }
};

const onPageChange = (page: number) => {
  pagination.value.current = page;
  if (!keyword.value.trim()) load();
};
const onPageSizeChange = (pageSize: number) => {
  pagination.value.pageSize = pageSize;
  pagination.value.current = 1;
  load();
};
const onSearch = () => {
  pagination.value.current = 1;
  load();
};
const onTreeSelect = (keys: string[]) => {
  const key = keys?.[0];
  if (!key) return;
  clearSelection();
  batchStatus.value = "";
  selectedTreeKeys.value = [key];
  breadcrumb.value = findPath(treeData.value, key) || [];
  const selected = breadcrumb.value[breadcrumb.value.length - 1];
  accountId.value = selected?.account_id;
  chatId.value = selected?.chat_id;
  topicId.value = selected?.topic_id;
  pagination.value.current = 1;
  load();
};
const resetTreeSelection = () => {
  clearSelection();
  batchStatus.value = "";
  selectedTreeKeys.value = [];
  breadcrumb.value = [];
  accountId.value = undefined;
  chatId.value = undefined;
  topicId.value = undefined;
  pagination.value.current = 1;
  load();
};
const toggleResourceSelection = (record: any, checked: boolean) => {
  const next = new Map(selectedResources.value);
  const id = String(record.id);
  if (checked) next.set(id, record);
  else next.delete(id);
  selectedResources.value = next;
};
const toggleCurrentPageSelection = (checked: boolean) => {
  const next = new Map(selectedResources.value);
  for (const record of rows.value) {
    const id = String(record.id);
    if (checked) next.set(id, record);
    else next.delete(id);
  }
  selectedResources.value = next;
};
const clearSelection = () => { selectedResources.value = new Map(); };
const formatSize = (bytes: number) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return (bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1) + " " + units[index];
};
const triggerDownload = (record: any) => {
  const link = document.createElement("a");
  link.href = `/resources/${encodeURIComponent(String(record.id))}/download`;
  link.download = record.filename || "";
  document.body.appendChild(link);
  link.click();
  link.remove();
};
const startBatchDownload = async () => {
  const queue = [...selectedResources.value.values()];
  if (!queue.length || batchRunning.value) return;
  batchRunning.value = true;
  batchStopRequested.value = false;
  let started = 0;
  let nextIndex = 0;
  batchStatus.value = "准备发起 " + queue.length + " 项下载";
  const worker = async () => {
    while (!batchStopRequested.value) {
      const index = nextIndex++;
      if (index >= queue.length) return;
      const record = queue[index];
      try {
        triggerDownload(record);
        started += 1;
      } catch {
        batchStatus.value = "发起下载时遇到错误（已发起 " + started + "/" + queue.length + " 项）";
      }
      batchStatus.value = "已发起 " + started + "/" + queue.length + " 项" + (batchStopRequested.value ? "，正在停止" : "");
      // Keep at most eight queue workers active and pace browser download prompts.
      await new Promise(resolve => window.setTimeout(resolve, 250));
    }
  };
  try {
    await Promise.all(Array.from({ length: Math.min(8, queue.length) }, () => worker()));
    batchStatus.value = batchStopRequested.value
      ? "已停止后续任务，已发起 " + started + "/" + queue.length + " 项"
      : "已发起全部 " + started + " 项下载；实际完成状态由浏览器下载管理器确认";
  } finally {
    batchRunning.value = false;
    batchStopRequested.value = false;
  }
};
const stopBatchDownload = () => {
  batchStopRequested.value = true;
  batchStatus.value = "正在停止后续任务…";
};
const downloadResource = (record: any) => triggerDownload(record);

const share = async (record: any) => {
  await createShareAPI(record.id);
  await load();
};
const removeShare = async (item: any) => {
  await deleteShareAPI(item.id);
  await load();
};
const applyDetailData = (data: any[]) => data.map((item: any) => ({
  ...item,
  visible: isDetailVisible(item.key)
}));
const hydrateRowDetails = async () => {
  if (!rows.value.length) return;
  const currentRows = rows.value;
  const detailedRows = await Promise.all(currentRows.map(async (record: any) => {
    const response = await getResourceAPI(record.id);
    const fields = Array.isArray(response.data?.data) ? response.data.data : [];
    return {
      ...record,
      _detailValues: Object.fromEntries(fields.map((item: any) => [item.key, item.value]))
    };
  }));
  rows.value = detailedRows;
  if (!detailRows.value.length && detailedRows.length) {
    const first = await getResourceAPI(detailedRows[0].id);
    detailRows.value = Array.isArray(first.data?.data) ? applyDetailData(first.data.data) : [];
  }
};
const detail = async (record: any) => {
  const response = await getResourceAPI(record.id);
  detailRows.value = Array.isArray(response.data?.data) ? applyDetailData(response.data.data) : [];
  detailOpen.value = true;
};
// Manual category assignment functions are disabled; retained as comments.
// const setCategories = (record: any) => {
//   currentId.value = record.id;
//   categoryText.value = (record.category_ids || []).join(",");
//   categoryOpen.value = true;
// };
// const saveCategories = async () => {
//   if (!currentId.value) return;
//   const ids = categoryText.value.split(",").map(value => Number(value.trim())).filter(value => Number.isInteger(value) && value > 0);
//   await setResourceCategoriesAPI(currentId.value, ids);
//   categoryOpen.value = false;
//   await load();
// };

Promise.all([
  load(),
  loadTree()
]);
</script>

<style scoped>
.snow-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.catalog-layout {
  display: flex;
  flex: 1 1 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  gap: 12px;
  align-items: stretch;
}
.tree-panel,
.resource-panel {
  min-width: 0;
  height: 100%;
  min-height: 0;
  background: var(--color-bg-1, var(--color-bg-2));
}
.tree-panel {
  box-sizing: border-box;
  min-width: 200px;
  max-width: 50%;
  flex: 0 0 280px;
  overflow: auto;
}
.tree-resizer {
  position: relative;
  z-index: 2;
  flex: 0 0 6px;
  margin: 0 -3px;
  cursor: col-resize;
  touch-action: none;
}
.tree-resizer::after {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 2px;
  width: 2px;
  background: var(--color-border-2);
  content: "";
}
.tree-resizer:hover::after {
  background: rgb(var(--primary-6));
}
.resource-panel {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  overflow: hidden;
}
.panel-title {
  display: flex;
  flex: 0 0 40px;
  align-items: center;
  height: 40px;
  padding: 0 16px;
}
.resource-panel-title {
  justify-content: space-between;
  gap: 16px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.resource-search {
  width: 260px;
  flex: 0 1 260px;
}
.tree-content {
  box-sizing: border-box;
  flex: 1 1 0;
  min-height: 0;
  padding: 16px 12px;
  overflow: auto;
}
.tree-search {
  margin-bottom: 12px;
}
.tree-spin {
  display: block;
  min-height: 100px;
}
.tree-node-title {
  white-space: nowrap;
}
.resource-content {
  box-sizing: border-box;
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
  padding: 16px 16px 8px;
  overflow: hidden;
}
.resource-content :deep(.arco-table-wrapper) {
  flex: 1 1 0;
  min-height: 0;
}
.resource-content :deep(.arco-table) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.resource-content :deep(.arco-table-container) {
  flex: 1 1 0;
  min-height: 0;
}
.resource-content :deep(.arco-table-pagination) {
  flex: 0 0 auto;
  margin: 0;
  padding: 12px 0 4px;
  background: var(--color-bg-1, var(--color-bg-2));
}
.detail-row {
  display: grid;
  grid-template-columns: minmax(140px, 220px) minmax(0, 1fr);
  align-items: start;
  gap: 12px;
}
.detail-value {
  min-width: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
@media (max-width: 768px) {
  .snow-page {
    height: auto;
    min-height: 0;
    overflow: visible;
  }
  .catalog-layout {
    display: block;
    height: auto;
    min-height: 0;
    overflow: visible;
  }
  .tree-panel {
    width: 100% !important;
    max-width: 100%;
    height: auto;
    max-height: 240px;
    flex-basis: auto !important;
  }
  .tree-resizer {
    display: none;
  }
  .resource-panel-title {
    height: auto;
    min-height: 40px;
    flex-wrap: wrap;
    padding-top: 8px;
    padding-bottom: 8px;
  }
  .header-actions {
    width: 100%;
  }
  .resource-search {
    width: 100%;
    flex: 1 1 0;
  }
  .resource-panel {
    width: 100%;
    height: auto;
    min-height: 420px;
    margin-top: 12px;
    overflow: visible;
  }
  .resource-content {
    display: block;
    overflow: visible;
  }
  .resource-content :deep(.arco-table-wrapper),
  .resource-content :deep(.arco-table) {
    height: auto;
  }
  .resource-content :deep(.arco-table-container) {
    min-height: auto;
  }
}
</style>