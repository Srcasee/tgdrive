<template>
  <div class="snow-page">
    <a-spin :loading="loading" class="container" tip="loading...">
      <a-card :bordered="false">
        <a-row align="center">
          <a-col :span="isMobile ? 24 : 2">
            <div :class="{ center: isMobile }">
              <a-avatar :size="100" trigger-type="mask" @click="chooseAvatar">
                <img alt="avatar" :src="userInfo.avatar_url || defaultAvatar" />
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
              </a-tab-pane>
              <a-tab-pane key="totp" title="动态口令">
                <TotpSettings />
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
const defaultAvatar = "data:image/webp;base64,UklGRkYFAABXRUJQVlA4IDoFAABQJQCdASqAAIAAPwF0sVSrJiQophQLYWAgCWUAz2RrHxZLF3RFa6+kpqujeA+r2e/TDnHi6kohtoNd0nBYiLvwMYFsFfOhctQWwpuCxA/OuA7tA5+JAZIKZieX5ANDHlKMEoSr+ahXcjvByN2R0Trc+8yyRZnyHCtB1ROyAU+/1xkQaqtG0UgdOcBVOGBEAT4hApLqvNvb0hdzXIQ4kEb8hbzHcm8lsXhKi7ke77+TBp7YZSs5lizE2xA9bM/TwMmtbJMxiBS0G/F8VpTxWNC5bcG8hvWvxwCuvO7j5c/66v0QPFUtye5iduHqYJzJ2UujVYj0q5ybtWBi5vFJdZc0QhSkZLqfqv/nDVaa/TjCiQbIVVk7dOvldikKfOF37vc40/43csHyN4GSdrmX1FaExwAqAP700KW6XfqD9qefqW2PBrjQIChmpCIKLtKhQe/SFQxGRit4HpLGmMmSehO3TZzY7QDu2fbxDhA1ocmgbPdRfsaddj0kBh4jYewFYUmYQADqsGXxUbYdOnSyd8hYshR/YK7nX1MHEp6Wz+dseekJhDfCvFB+YuhUMnd8grcoAO7cfbrIzBPDBOCc+UTyabGImuEfvBRX5hEJdtAAeW3hu/9v90j9YXS6c+3bbkaUEdYMENdzaWibjmXix0lzrPgb/PpI62rQRl5ulBPWCcfkuVPBQQpzM8MB4GOib6XCgBV2JsBv0byKZmVHwhFhunpF2GpCQ7GyVFRGf2wQwTqHJe8iaJxa2UsgmolpYXvgM2iv8Rfbu4YX+QWnkIy3/jfRQeDDxoBU7WvLAinxDvOelDWJmW+i4pZ2qAnu9b8gDHsOpHUHaDEEUsWoIgzsN0jhCHZnjoBZX4BFUNLtdkaH1cc8N4/rnoWbQJKx/C3Aydnq9hY0r6KY0H2FkIRhj/oHShHtGaSE5mCbA+hlOjNcffDJQ2mGXzr/f6Gei/qTHAflzOYt11vLbgyWxUO59MEbgZQnDcto7LqoG9kky462d8g+crZLu8Nvh2pnl/ddO9V4A7KANuTLZj6RMVR9cLb//gNsULl5a7eWyTNi3u2UJC74xqj02zSdQCO3pVSRArCGJLD8dQ1J02Gr0zGzVeZ6a+jpf4LkOqF+QFysjL9gS89D2+9NxpeaK5SAbN5v9yJcuXcBXmIGUWAasVR6H0thz9i/p17vP7FO+++UolAFaAP0eTSqp/hTmuh9N6TZQcnuWEyL7Z4A+l7NETuekqfocmpQywkRk38BY3aqY8N7rWooFHcqRI5pGQD/okC8BGfdwb7wk0JUqlqnuC8fut5V0qO+2fqkTAZsegwzCIKWyULRX0vZrDMW25vR+b/4zihtGUSlasIsQF8YC9DzX9JwX0ZtiYOtQ65qrqS/ca1IuBWbdx8odv+FxhZyr8ag62+pOnmT2SweDWY5MPJCGaWnPXKzW4xkSXA+VSU8P9eea/oz4uCXXw7c0f9/xND+cUvbR/CNMpq4FcomLk1objjDDGEsx+IISM4DQubJhjLdVs6yY7U3q4jaDp50LpYmIagN2oy0ZI1ISKwNVoo1YSGVguiospH06L8lko03ofc0vahPAr/FhQ/crYseBhA+LfSZAI/f9ogmrm/NDUsga+IF7FIvAhV+RGmsWZm8NA8pQvE1WulhuzxCoW/G2npZFwSrM58RUeE83IDj9fdAhQByN4orfB8iNNpP3Qm5wZDG/zlMUekZWverF7ZUY2blGhfh6iOfI6SQPerKvt1Hiau7UrUllkcuffo5wnL8GRc4AuAYrQAAAA==";

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
