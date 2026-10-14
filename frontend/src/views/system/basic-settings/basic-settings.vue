<template>
  <div class="snow-page">
    <a-spin :loading="loading" class="container" tip="loading...">
      <a-card :bordered="false">
        <a-row align="center">
          <a-col :span="isMobile ? 24 : 2">
            <div :class="{ center: isMobile }">
              <a-avatar :size="100" trigger-type="mask" @click="chooseAvatar">
                <img v-if="userInfo.avatar_url" alt="avatar" :src="userInfo.avatar_url" />
                <span v-else>{{ userInfo.username?.slice(0, 1)?.toUpperCase() || "U" }}</span>
                <template #trigger-icon>
                  <IconEdit />
                </template>
              </a-avatar>
              <input
                ref="avatarInput"
                class="avatar-input"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                @change="onAvatarSelected"
              />
            </div>
          </a-col>
          <a-col :span="isMobile ? 24 : 22">
            <a-space direction="vertical" size="large">
              <a-descriptions
                title="用户资料"
                :data="profileDetails"
                :column="descriptionsColumn(1, 4)"
                :align="{ label: 'right' }"
              />
            </a-space>
          </a-col>
        </a-row>
      </a-card>
      <a-card class="margin-top" :bordered="false">
        <a-row align="center">
          <a-col :span="24">
            <a-tabs type="rounded" size="medium">
              <a-tab-pane key="security" title="安全设置">
                <SecuritySettings v-model="userInfo" @refresh="refresh" />
                <TotpSettings class="margin-top" />
              </a-tab-pane>
            </a-tabs>
          </a-col>
        </a-row>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import SecuritySettings from "@/views/system/basic-settings/components/security-settings.vue";
import TotpSettings from "@/views/system/basic-settings/components/totp-settings.vue";
import useGlobalProperties from "@/hooks/useGlobalProperties";
import { useDevicesSize } from "@/hooks/useDevicesSize";
import { useLayoutModel } from "@/hooks/useLayoutModel";
import { getUserInfoAPI, updateUserAvatarAPI } from "@/api/modules/user";
import { useRouteConfigStore } from "@/store/modules/route-config";
import { useUserInfoStore } from "@/store/modules/user-info";

const proxy = useGlobalProperties();
const routerStore = useRouteConfigStore();
const userStore = useUserInfoStore();
const { isMobile } = useDevicesSize();
const { descriptionsColumn } = useLayoutModel();
const loading = ref(false);
const uploadingAvatar = ref(false);
const avatarInput = ref<HTMLInputElement>();
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

const chooseAvatar = () => {
  if (!uploadingAvatar.value) avatarInput.value?.click();
};

const onAvatarSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    proxy.$message.warning("仅支持 JPG、PNG 或 WebP 图片");
    input.value = "";
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    proxy.$message.warning("头像文件不能超过 2 MB");
    input.value = "";
    return;
  }

  try {
    uploadingAvatar.value = true;
    const result = await updateUserAvatarAPI(file);
    userInfo.value = { ...userInfo.value, ...result.data };
    userStore.account.user = { ...userStore.account.user, ...result.data };
    proxy.$message.success("头像更新成功");
  } catch (error: any) {
    proxy.$message.error(error?.response?.data?.detail || "头像上传失败，请重试");
  } finally {
    uploadingAvatar.value = false;
    input.value = "";
  }
};

const refresh = () => {
  void getUserInfo();
};

void getUserInfo();
routerStore.setTabsTitle("基本设置");
</script>

<style lang="scss" scoped>
.container {
  display: flex;
  flex-direction: column;
}
.margin-top {
  margin-top: $padding;
}
.center {
  display: flex;
  justify-content: center;
}
.avatar-input {
  display: none;
}
</style>
