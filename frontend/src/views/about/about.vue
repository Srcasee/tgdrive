<template>
  <div class="snow-page">
    <a-card title="简介">
      <div>
        <p>TGDrive 是面向 Telegram 的文件目录与分发系统，支持账号管理、频道资源整理、分类和下载任务管理。</p>
        <p>通过统一的资源目录管理 Telegram 中的文件，并提供资源分类和分发能力。</p>
        <p>本项目持续围绕 Telegram 资源管理与交付场景迭代。</p>
      </div>
    </a-card>
    <a-card class="margin-top" title="项目信息">
      <a-descriptions :column="descriptionsColumn(1, 2)" bordered>
        <a-descriptions-item v-for="item of projectInfo" :key="item.label" :label="item.label">
          <a-link :href="item.value" v-if="item.link" target="_blank">{{ item.label }}</a-link>
          <span v-else>{{ item.value }}</span>
        </a-descriptions-item>
      </a-descriptions>
    </a-card>
    <a-card class="margin-top" title="生产环境依赖">
      <a-descriptions :data="dependencies" bordered :layout="descriptionsLayout" :column="descriptionsColumn(1, 2)" />
    </a-card>
    <a-card class="margin-top" title="开发环境依赖">
      <a-descriptions :data="devDependencies" bordered :layout="descriptionsLayout" :column="descriptionsColumn(1, 2)" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import packageJson from "../../../package.json";
import { useLayoutModel } from "@/hooks/useLayoutModel";

const { descriptionsLayout, descriptionsColumn } = useLayoutModel();

const projectInfo: any = [
  {
    label: "项目名称",
    link: false,
    value: "TGDrive"
  },
  {
    label: "GitHub",
    link: true,
    value: "https://github.com/Srcasee/tgdrive"
  },
];

const dependencies = ref<any>([]);
const devDependencies = ref<any>([]);

const init = () => {
  dependencies.value.length = 0;
  devDependencies.value.length = 0;
  Object.entries(packageJson.dependencies).forEach(item => {
    dependencies.value.push({ label: item[0], value: item[1] });
  });
  Object.entries(packageJson.devDependencies).forEach(item => {
    devDependencies.value.push({ label: item[0], value: item[1] });
  });
};
init();
</script>

<style lang="scss" scoped>
.margin-top {
  margin-top: $margin;
}
</style>
