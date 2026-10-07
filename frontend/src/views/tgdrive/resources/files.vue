<template>
  <div class="snow-page">
    <a-card title="资源文件">
      <a-space class="toolbar">
        <a-input-search v-model="keyword" placeholder="搜索文件名" style="width: 320px" @search="load" />
        <a-select v-model="categoryId" allow-clear placeholder="分类" style="width: 180px" @change="load">
          <a-option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</a-option>
        </a-select>
      </a-space>
      <a-table :data="rows" :loading="loading" :pagination="pagination">
        <template #columns>
          <a-table-column title="ID" data-index="id" />
          <a-table-column title="详情"><template #cell="{ record }"><a-button size="small" @click="detail(record)">查看</a-button><a-button size="small" @click="setCategories(record)">分类</a-button></template></a-table-column>
          <a-table-column title="文件名" data-index="filename" />
          <a-table-column title="大小" data-index="size" />
          <a-table-column title="类型" data-index="mime_type" />
          <a-table-column title="来源数" data-index="source_count" />
          <a-table-column title="分类"><template #cell="{ record }">{{ (record.category_ids || []).join(", ") || "未分类" }}</template></a-table-column>
          <a-table-column title="分享">
            <template #cell="{ record }"><a-space><a-button size="small" @click="share(record)">创建</a-button><a-button v-for="s in (record.shares || [])" :key="s.id" size="small" status="danger" @click="removeShare(s)">删除 {{ s.id }}</a-button></a-space></template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
    <a-modal v-model:visible="detailOpen" title="资源详情" hide-cancel @ok="detailOpen=false"><a-descriptions :data="detailRows" :column="1" /></a-modal>
    <a-modal v-model:visible="categoryOpen" title="设置分类" @ok="saveCategories"><a-input v-model="categoryText" placeholder="分类 ID，逗号分隔" /></a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { getResourcesAPI, getResourceAPI, searchResourcesAPI, getCategoriesAPI, createShareAPI, deleteShareAPI, setResourceCategoriesAPI } from "@/api/modules/tgdrive";
const rows=ref<any[]>([]), categories=ref<any[]>([]), loading=ref(false), keyword=ref(""), categoryId=ref<number>();
const detailOpen=ref(false), categoryOpen=ref(false), currentId=ref<number>(), categoryText=ref(""), detailRows=ref<any[]>([]);
const pagination=ref({pageSize:20});
const load=async()=>{loading.value=true;try{const r=keyword.value?await searchResourcesAPI({q:keyword.value,category_id:categoryId.value}):await getResourcesAPI({page:1,size:100,category_id:categoryId.value});rows.value=r.data?.items||r.data||[]}finally{loading.value=false}};
const share=async(r:any)=>{await createShareAPI(r.id);await load()};
const removeShare=async(s:any)=>{await deleteShareAPI(s.id);await load()};
const detail=async(r:any)=>{const x=(await getResourceAPI(r.id)).data;detailRows.value=Object.entries(x||{}).map(([label,value])=>({label,value:String(value??"")}));detailOpen.value=true};
const setCategories=async(r:any)=>{currentId.value=r.id;categoryText.value=(r.category_ids||[]).join(",");categoryOpen.value=true};
const saveCategories=async()=>{if(!currentId.value)return;const ids=categoryText.value.split(",").map(x=>Number(x.trim())).filter(x=>Number.isInteger(x)&&x>0);await setResourceCategoriesAPI(currentId.value,ids);categoryOpen.value=false;await load()};
Promise.all([load(),getCategoriesAPI().then(r=>categories.value=r.data||[])]);
</script>

<style scoped>.toolbar{margin-bottom:16px;}</style>
