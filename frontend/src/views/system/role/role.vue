<template>
  <div class="snow-page">
    <div class="snow-inner">
      <s-layout-tools>
        <template #left>
          <a-space wrap>
            <a-input v-model="form.name" placeholder="请输入角色名称" allow-clear />
            <a-input v-model="form.code" placeholder="请输入角色标识" allow-clear />
            <a-select v-model="form.status" placeholder="角色状态" style="width: 120px" allow-clear>
              <a-option v-for="item in openState" :key="item.value" :value="item.value">{{ item.name }}</a-option>
            </a-select>
            <a-button type="primary" @click="search"><template #icon><icon-search /></template>查询</a-button>
            <a-button @click="reset"><template #icon><icon-refresh /></template>重置</a-button>
          </a-space>
        </template>
        <template #right>
          <a-space wrap>
            <a-button type="primary" @click="onAdd"><template #icon><icon-plus /></template>新增</a-button>
            <a-popconfirm content="确定删除选中的角色吗？系统管理员角色不可删除，仍被用户使用的角色也无法删除。" type="warning" @ok="removeSelected">
              <a-button status="danger" :disabled="selectedKeys.length === 0"><template #icon><icon-delete /></template>批量删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </s-layout-tools>
      <a-table
        row-key="id"
        :data="filteredRoleList"
        :bordered="{ cell: true }"
        :loading="loading"
        :scroll="{ x: '100%', minWidth: 1000 }"
        :pagination="pagination"
        :row-selection="{ type: 'checkbox', showCheckedAll: true }"
        :selected-keys="selectedKeys"
        @select="select"
        @select-all="selectAll"
      >
        <template #columns>
          <a-table-column title="序号" :width="64"><template #cell="{ rowIndex }">{{ rowIndex + 1 }}</template></a-table-column>
          <a-table-column title="角色名称" data-index="name" :width="150" ellipsis tooltip />
          <a-table-column title="角色标识" data-index="code" :width="140" ellipsis tooltip />
          <a-table-column title="排序" data-index="sort" :width="90" align="center" />
          <a-table-column title="状态" :width="100" align="center">
            <template #cell="{ record }">
              <a-tag bordered size="small" :color="record.status === 1 ? 'arcoblue' : 'red'">{{ record.status === 1 ? "启用" : "禁用" }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="描述" data-index="description" ellipsis tooltip />
          <a-table-column title="创建时间" data-index="createTime" :width="180" />
          <a-table-column title="操作" :width="280" align="center" :fixed="tableFixed">
            <template #cell="{ record }">
              <a-space>
                <a-button type="primary" status="success" size="mini" :disabled="record.admin" @click="onPrivileges(record)">
                  <template #icon><icon-safe /></template>分配权限
                </a-button>
                <a-button type="primary" size="mini" :disabled="record.admin" @click="onUpdate(record)">
                  <template #icon><icon-edit /></template>修改
                </a-button>
                <a-popconfirm content="确定删除该角色吗？" type="warning" @ok="removeRole(record)">
                  <a-button type="primary" status="danger" size="mini" :disabled="record.admin">
                    <template #icon><icon-delete /></template>删除
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </div>

    <a-modal :width="dialogWidth()" v-model:visible="open" :mask-closable="false" @close="afterClose" @ok="handleOk" @cancel="afterClose">
      <template #title>{{ title }}</template>
      <a-form ref="formRef" auto-label-width :layout="formLayout" :rules="rules" :model="addForm">
        <a-form-item field="name" label="角色名称" validate-trigger="blur">
          <a-input v-model="addForm.name" placeholder="请输入角色名称" allow-clear />
        </a-form-item>
        <a-form-item field="code" label="角色编码" validate-trigger="blur">
          <a-input v-model="addForm.code" placeholder="小写字母开头，可包含数字、下划线和连字符" allow-clear />
        </a-form-item>
        <a-form-item field="status" label="状态">
          <a-switch type="round" :checked-value="1" :unchecked-value="0" v-model="addForm.status">
            <template #checked>启用</template><template #unchecked>禁用</template>
          </a-switch>
        </a-form-item>
        <a-form-item field="sort" label="排序">
          <a-input-number v-model="addForm.sort" :step="1" :precision="0" :min="0" :max="9999" :style="{ width: '150px' }" />
        </a-form-item>
        <a-form-item field="description" label="描述">
          <a-textarea v-model="addForm.description" placeholder="请输入描述" allow-clear />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer v-model:visible="drawerOpen" :width="dialogWidth('500px', '100%')" @ok="drawerOk" @cancel="drawerCancel">
      <template #title>分配权限：{{ activeRole?.name || "" }}</template>
      <a-space direction="vertical" fill>
        <a-card>
          <a-row :gutter="16" align="center">
            <a-col :span="12">
              <span class="text-right-gap">展开全部</span>
              <a-switch type="round" v-model="treeSwitch.expandAll" @change="onExpandAll" />
            </a-col>
            <a-col :span="12">
              <span class="text-right-gap">全选节点</span>
              <a-switch type="round" v-model="treeSwitch.selectAll" @change="onSelectAll" />
            </a-col>
          </a-row>
        </a-card>
        <a-tree
          ref="treeRef"
          :field-names="{ key: 'id', title: 'i18n', children: 'children' }"
          :check-strictly="true"
          checkable
          show-line
          v-model:checked-keys="permissionKeys"
          :data="permissionTree"
        />
      </a-space>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import useGlobalProperties from "@/hooks/useGlobalProperties";
import {
  getRoleAPI,
  createRoleAPI,
  updateRoleAPI,
  deleteRoleAPI,
  getMenuListAPI,
  getUserPermissionAPI,
  updateRolePermissionsAPI
} from "@/api/modules/system/index";
import { deepClone } from "@/utils";
import { useLayoutModel } from "@/hooks/useLayoutModel";

const proxy = useGlobalProperties();
const openState = ref(dictFilter("status"));
const { dialogWidth, formLayout, tableFixed } = useLayoutModel();
const form = ref<any>({ name: "", code: "", status: undefined });
const loading = ref(false);
const roleList = ref<any[]>([]);
const selectedKeys = ref<any[]>([]);
const pagination = ref({ pageSize: 10, showPageSize: true });
const filteredRoleList = computed(() => roleList.value.filter((role: any) =>
  (!form.value.name || role.name?.toLowerCase().includes(form.value.name.toLowerCase())) &&
  (!form.value.code || role.code?.toLowerCase().includes(form.value.code.toLowerCase())) &&
  (form.value.status === undefined || form.value.status === null || form.value.status === "" || role.status === form.value.status)
));

const getRole = async () => {
  loading.value = true;
  try {
    const result: any = await getRoleAPI();
    roleList.value = Array.isArray(result) ? result : (result.data || []);
    selectedKeys.value = selectedKeys.value.filter(id => roleList.value.some(role => role.id === id));
  } catch (error: any) {
    arcoMessage("error", error?.response?.data?.detail || "获取角色列表失败");
  } finally {
    loading.value = false;
  }
};
const search = () => { pagination.value = { ...pagination.value, current: 1 } as any; };
const reset = () => { form.value = { name: "", code: "", status: undefined }; pagination.value = { ...pagination.value, current: 1 } as any; };

const open = ref(false);
const title = ref("");
const editingId = ref<number | null>(null);
const formRef = ref();
const addForm = ref<any>({ name: "", code: "", status: 1, sort: 1, description: "" });
const rules = {
  name: [{ required: true, message: "请输入角色名称" }],
  code: [{ required: true, message: "请输入角色编码" }]
};
const onAdd = () => {
  editingId.value = null;
  title.value = "新增角色";
  addForm.value = { name: "", code: "", status: 1, sort: 1, description: "" };
  open.value = true;
};
const onUpdate = (row: any) => {
  editingId.value = row.id;
  title.value = "修改角色";
  addForm.value = deepClone(row);
  open.value = true;
};
const handleOk = async () => {
  const invalid = await formRef.value?.validate();
  if (invalid) return;
  const payload = {
    name: addForm.value.name.trim(),
    code: addForm.value.code.trim(),
    status: addForm.value.status,
    sort: addForm.value.sort,
    description: addForm.value.description || ""
  };
  try {
    if (editingId.value === null) await createRoleAPI(payload);
    else await updateRoleAPI(editingId.value, payload);
    arcoMessage("success", editingId.value === null ? "角色创建成功" : "角色更新成功");
    open.value = false;
    afterClose();
    await getRole();
  } catch (error: any) {
    arcoMessage("error", error?.response?.data?.detail || error?.message || "保存角色失败");
  }
};
const afterClose = () => {
  formRef.value?.resetFields?.();
  addForm.value = { name: "", code: "", status: 1, sort: 1, description: "" };
  editingId.value = null;
};
const removeRole = async (row: any) => {
  try {
    await deleteRoleAPI(row.id);
    arcoMessage("success", "角色已删除");
    selectedKeys.value = selectedKeys.value.filter(id => id !== row.id);
    await getRole();
  } catch (error: any) {
    arcoMessage("error", error?.response?.data?.detail || "删除角色失败");
  }
};
const removeSelected = async () => {
  const ids = [...selectedKeys.value];
  for (const id of ids) {
    try {
      await deleteRoleAPI(id);
    } catch (error: any) {
      arcoMessage("error", error?.response?.data?.detail || `角色 ${id} 删除失败`);
    }
  }
  selectedKeys.value = [];
  await getRole();
};
const select = (keys: any[]) => { selectedKeys.value = keys; };
const selectAll = (state: boolean) => { selectedKeys.value = state ? filteredRoleList.value.map((item: any) => item.id) : []; };

const treeRef = ref();
const treeSwitch = ref({ expandAll: true, selectAll: false });
const permissionTree = ref<any[]>([]);
const permissionKeys = ref<string[]>([]);
const activeRole = ref<any>(null);
const drawerOpen = ref(false);
const onExpandAll = (state: boolean) => treeRef.value?.expandAll?.(state);
const onSelectAll = (state: boolean) => treeRef.value?.checkAll?.(state);
const treeSwitchReset = () => { treeSwitch.value = { expandAll: true, selectAll: false }; };
const translation = (tree: any[]) => tree.forEach((item: any) => {
  if (item.children?.length) translation(item.children);
  if (item.meta?.title) item.i18n = proxy.$t(`menu.${item.meta.title}`);
});
const getMenuList = async () => {
  const result: any = await getMenuListAPI();
  const data = result.data || [];
  translation(data);
  permissionTree.value = data;
};
const onPrivileges = async (row: any) => {
  try {
    activeRole.value = row;
    const result: any = await getUserPermissionAPI({ role: row.code });
    permissionKeys.value = (Array.isArray(result) ? result : result.data || []).map(String);
    drawerOpen.value = true;
    treeSwitchReset();
    await nextTick();
    treeRef.value?.expandAll?.(true);
  } catch (error: any) {
    arcoMessage("error", error?.response?.data?.detail || "读取角色权限失败");
  }
};
const drawerOk = async () => {
  if (!activeRole.value) return;
  try {
    await updateRolePermissionsAPI(activeRole.value.id, permissionKeys.value.map(String));
    arcoMessage("success", "角色权限已保存");
    drawerOpen.value = false;
    treeSwitchReset();
    await getRole();
  } catch (error: any) {
    arcoMessage("error", error?.response?.data?.detail || "保存角色权限失败");
  }
};
const drawerCancel = () => { drawerOpen.value = false; treeSwitchReset(); activeRole.value = null; };

getRole();
getMenuList();
</script>

<style lang="scss" scoped>
.text-right-gap { margin-right: $margin; }
</style>
