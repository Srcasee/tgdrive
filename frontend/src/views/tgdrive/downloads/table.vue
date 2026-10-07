<template>
  <a-table :data="rows" row-key="id">
    <template #columns>
      <a-table-column title="ID" data-index="id" /><a-table-column title="文件" data-index="filename" />
      <a-table-column title="状态" data-index="status" /><a-table-column title="已传输字节" data-index="bytes_transferred" />
      <a-table-column title="开始时间" data-index="started_at" /><a-table-column title="完成时间" data-index="finished_at" />
      <a-table-column title="错误" data-index="error" />
      <a-table-column title="操作"><template #cell="{record}"><a-popconfirm content="删除该记录吗？" @ok="$emit('remove',record.id)"><a-button size="small" status="danger">删除</a-button></a-popconfirm></template></a-table-column>
    </template>
  </a-table>
</template>
<script setup lang="ts">
defineProps<{rows:any[];active:boolean}>();
defineEmits<{remove:[id:number]}>();
</script>
