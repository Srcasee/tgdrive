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
          <a-input-search v-model="keyword" placeholder="搜索文件名" class="resource-search" @search="onSearch" />
        </div>
        <a-divider margin="0" />
        <div class="resource-content">
          <a-space class="toolbar" wrap>
            <a-button @click="resetTreeSelection">全部资源</a-button>
          </a-space>
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
              <a-table-column title="详情" :width="120">
                <template #cell="{ record }">
                  <a-space>
                    <a-button size="small" @click="detail(record)">查看</a-button>
                    <!-- Manual category assignment is disabled; original control retained as a comment.
                    <a-button size="small" @click="setCategories(record)">分类</a-button>
                    -->
                  </a-space>
                </template>
              </a-table-column>
              <a-table-column title="文件名" data-index="filename" />
              <a-table-column title="大小" data-index="size" :width="100" />
              <a-table-column title="类型" data-index="mime_type" :width="130" />
              <a-table-column title="来源数" data-index="source_count" :width="90" />
              <a-table-column title="分享" :width="180">
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
        <a-checkbox :model-value="allDetailsVisible" :indeterminate="someDetailsVisible" @change="toggleAllDetails">全部显示</a-checkbox>
        <a-divider margin="0" />
        <div v-for="item in detailRows" :key="item.key" class="detail-row">
          <a-checkbox v-model="item.visible">{{ item.label }}</a-checkbox>
          <div v-if="item.visible" class="detail-value">{{ item.value }}</div>
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
// Manual category assignment state is disabled; retained as comments.
// const categoryOpen = ref(false);
// const currentId = ref<number>();
// const categoryText = ref("");
type DetailItem = { key: string; label: string; value: string; visible: boolean };
const detailRows = ref<DetailItem[]>([]);
const allDetailsVisible = computed(() => detailRows.value.length > 0 && detailRows.value.every(item => item.visible));
const someDetailsVisible = computed(() => detailRows.value.some(item => item.visible) && !allDetailsVisible.value);
const toggleAllDetails = (visible: boolean) => detailRows.value.forEach(item => item.visible = visible);
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
    } else {
      const response = await getResourcesAPI({
        page: pagination.value.current,
        size: pagination.value.pageSize,
        ...params
      });
      const payload = response.data?.data;
      rows.value = Array.isArray(payload?.items) ? payload.items : Array.isArray(payload) ? payload : [];
      pagination.value.total = Number(payload?.total ?? rows.value.length);
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
  selectedTreeKeys.value = [];
  breadcrumb.value = [];
  accountId.value = undefined;
  chatId.value = undefined;
  topicId.value = undefined;
  pagination.value.current = 1;
  load();
};
const share = async (record: any) => {
  await createShareAPI(record.id);
  await load();
};
const removeShare = async (item: any) => {
  await deleteShareAPI(item.id);
  await load();
};
const detail = async (record: any) => {
  const response = await getResourceAPI(record.id);
  detailRows.value = Array.isArray(response.data?.data)
    ? response.data.data.map((item: any) => ({ ...item, visible: true }))
    : [];
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
.toolbar {
  margin-bottom: 16px;
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
  .resource-search {
    width: 100%;
    flex: 1 1 100%;
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