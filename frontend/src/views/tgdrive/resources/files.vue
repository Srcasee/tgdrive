<template>
  <div class="snow-page">
    <div class="catalog-layout">
      <aside class="tree-panel">
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
      <section class="resource-panel">
        <div class="panel-title">
          <a-breadcrumb>
            <a-breadcrumb-item v-for="item in breadcrumb" :key="item.key">{{ item.title }}</a-breadcrumb-item>
            <a-breadcrumb-item v-if="!breadcrumb.length">全部资源</a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <a-divider margin="0" />
        <div class="resource-content">
          <a-space class="toolbar" wrap>
            <a-input-search v-model="keyword" placeholder="搜索文件名" style="width: 260px" @search="onSearch" />
            <a-select v-model="categoryId" allow-clear placeholder="分类" style="width: 160px" @change="onFilterChange">
              <a-option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</a-option>
            </a-select>
            <a-button @click="resetTreeSelection">全部资源</a-button>
          </a-space>
          <a-table
            :data="rows"
            :loading="loading"
            :pagination="pagination"
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
              <a-table-column title="分类" :width="130">
                <template #cell="{ record }">{{ (record.category_ids || []).join(", ") || "未分类" }}</template>
              </a-table-column>
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
    <a-modal v-model:visible="detailOpen" title="资源详情" hide-cancel @ok="detailOpen=false">
      <a-descriptions :data="detailRows" :column="1" />
    </a-modal>
    <!-- Manual category assignment is disabled; original dialog retained as a comment.
    <a-modal v-model:visible="categoryOpen" title="设置分类" @ok="saveCategories">
      <a-input v-model="categoryText" placeholder="分类 ID，逗号分隔" />
    </a-modal>
    -->
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import {
  getResourcesAPI, getResourceAPI, searchResourcesAPI, getCategoriesAPI, getResourceTreeAPI,
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

const rows = ref<any[]>([]);
const categories = ref<any[]>([]);
const loading = ref(false);
const treeLoading = ref(false);
const keyword = ref("");
const treeKeyword = ref("");
const categoryId = ref<number>();
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
const detailRows = ref<any[]>([]);
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
      category_id: categoryId.value,
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
const onFilterChange = () => {
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
  detailRows.value = Object.entries(response.data?.data || {}).map(([label, value]) => ({
    label,
    value: String(value ?? "")
  }));
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
  loadTree(),
  getCategoriesAPI().then(response => categories.value = response.data?.data || response.data || [])
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
  width: 280px;
  min-width: 200px;
  max-width: 50%;
  flex: 0 0 280px;
  resize: horizontal;
  overflow: auto;
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
  flex: 1 1 0;
  min-height: 0;
  padding: 16px 16px 12px;
  overflow: auto;
}
.toolbar {
  margin-bottom: 16px;
}
:deep(.arco-table-pagination) {
  margin: 16px 0 8px;
  padding: 0 0 8px;
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
    width: 100%;
    max-width: 100%;
    height: auto;
    max-height: 240px;
    resize: vertical;
  }
  .resource-panel {
    width: 100%;
    height: auto;
    min-height: 420px;
    margin-top: 12px;
    overflow: visible;
  }
  .resource-content {
    overflow: visible;
  }
}
</style>