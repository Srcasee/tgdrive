<template>
  <div class="snow-page">
    <a-result status="info" title="人工分类功能已禁用" sub-title="分类的新增、修改、删除和资源手动归类暂时关闭。" />
    <!-- 原资源分类管理界面保留为注释，便于后续恢复。
    <div class="snow-page">
      <a-card title="资源分类">
        <template #extra><a-button type="primary" @click="add">新增分类</a-button></template>
        <a-table :data="rows" row-key="id">
          <template #columns>
            <a-table-column title="ID" data-index="id" />
            <a-table-column title="名称" data-index="name" />
            <a-table-column title="操作">
              <template #cell="{record}">
                <a-space>
                  <a-button size="small" @click="edit(record)">修改</a-button>
                  <a-popconfirm content="确定删除吗？" @ok="remove(record)">
                    <a-button size="small" status="danger">删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
      <a-modal v-model:visible="open" :title="editing ? '修改分类' : '新增分类'" @ok="save">
        <a-input v-model="name" placeholder="分类名称" />
      </a-modal>
    </div>
    -->
  </div>
</template>

<script setup lang="ts">
// 人工分类管理页面已禁用；原逻辑保留为注释，避免删除业务代码。
// import { ref } from "vue";
// import { getCategoriesAPI, createCategoryAPI, updateCategoryAPI, deleteCategoryAPI } from "@/api/modules/tgdrive";
// const rows=ref<any[]>([]),open=ref(false),editing=ref<any>(null),name=ref("");
// const load=async()=>{rows.value=(await getCategoriesAPI()).data||[]};
// const add=()=>{editing.value=null;name.value="";open.value=true};
// const edit=(r:any)=>{editing.value=r;name.value=r.name;open.value=true};
// const save=async()=>{if(!name.value.trim())return; if(editing.value) await updateCategoryAPI(editing.value.id,name.value); else await createCategoryAPI(name.value);open.value=false;await load()};
// const remove=async(r:any)=>{await deleteCategoryAPI(r.id);await load()};
// load();
</script>
