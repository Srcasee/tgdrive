<template>
  <a-space direction="vertical" fill size="large">
    <a-typography-title :heading="3">系统概览</a-typography-title>
    <a-grid :cols="4" :col-gap="16">
      <a-grid-item>
        <a-card>
          <a-typography-text>当前账号</a-typography-text>
          <div class="dashboard-value">{{ user?.username || "-" }}</div>
        </a-card>
      </a-grid-item>
      <a-grid-item>
        <a-card>
          <a-typography-text>角色</a-typography-text>
          <div class="dashboard-value">{{ user?.role || "-" }}</div>
        </a-card>
      </a-grid-item>
      <a-grid-item>
        <a-card>
          <a-typography-text>系统</a-typography-text>
          <div class="dashboard-value">Telegram</div>
        </a-card>
      </a-grid-item>
      <a-grid-item>
        <a-card>
          <a-typography-text>状态</a-typography-text>
          <div class="dashboard-value">Online</div>
        </a-card>
      </a-grid-item>
    </a-grid>
    <a-card>
      <a-space>
        <a-button type="primary" @click="reconcile">立即同步 Telegram Dialog</a-button>
        <span class="muted">仅触发后端 reconciliation，不直接扫描消息内容。</span>
      </a-space>
    </a-card>
  </a-space>
</template>

<script setup lang="ts">
import { Message } from "@arco-design/web-vue";
import { telegram } from "../api";

defineProps<{ user: any }>();

async function reconcile() {
  await telegram.reconcile();
  Message.success("已触发 reconciliation");
}
</script>
