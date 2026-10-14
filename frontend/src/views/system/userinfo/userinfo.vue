<template>
  <div class="snow-page">
    <a-spin :loading="loading" tip="loading...">
      <a-card :bordered="false">
        <a-descriptions
          title="用户资料"
          :data="profileDetails"
          :column="descriptionsColumn(1, 3)"
          :align="{ label: 'right' }"
        />
      </a-card>
      <a-card class="margin-top" :bordered="false">
        <SecuritySettings v-model="userInfo" @refresh="refresh" />
      </a-card>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import SecuritySettings from "@/views/system/userinfo/components/security-settings.vue";
import { useLayoutModel } from "@/hooks/useLayoutModel";
import { getUserInfoAPI } from "@/api/modules/user";
import { useRouteConfigStore } from "@/store/modules/route-config";

const routerStore = useRouteConfigStore();
const { descriptionsColumn } = useLayoutModel();
const loading = ref(false);
const userInfo = ref<any>({});

const formatLoginTime = (value?: number | string | null) => {
  if (!value) return "-";
  const timestamp = Number(value);
  const date = new Date(timestamp < 1e12 ? timestamp * 1000 : timestamp);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString();
};

const profileDetails = computed(() => [
  {
    label: "当前登录角色",
    value: userInfo.value.role === "admin" ? "管理员" : userInfo.value.role === "user" ? "普通用户" : "-"
  },
  {
    label: "登录时间",
    value: formatLoginTime(userInfo.value.last_login_at)
  },
  {
    label: "登录 IP",
    value: userInfo.value.last_login_ip || "-"
  }
]);

const getUserInfo = async () => {
  try {
    loading.value = true;
    const result = await getUserInfoAPI();
    userInfo.value = result.data.user || {};
  } finally {
    loading.value = false;
  }
};

const refresh = () => {
  void getUserInfo();
};

void getUserInfo();
routerStore.setTabsTitle("用户信息");
</script>

<style lang="scss" scoped>
.margin-top {
  margin-top: $padding;
}
</style>
