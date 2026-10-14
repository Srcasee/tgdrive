<template>
  <div class="header_setting" :class="isMobile && 'head-absolute-fix'">
    <!-- 国际化 -->
    <a-dropdown trigger="hover" @select="onLange">
      <a-button size="mini" type="text" class="icon_btn" id="system-language">
        <template #icon>
          <icon-language :size="18" />
        </template>
      </a-button>
      <template #content>
        <a-doption :disabled="language === 'zh-CN'">{{ $t(`system.zh-CN`) }}</a-doption>
        <a-doption :disabled="language === 'en-US'">{{ $t(`system.en-US`) }}</a-doption>
      </template>
    </a-dropdown>
    <!-- 切换黑夜模式 -->
    <a-tooltip :content="$t(`system.${!darkMode ? 'switch-to-night-mode' : 'switch-to-daytime-mode'}`)">
      <a-button size="mini" type="text" class="icon_btn" id="system-dark" @click="onNightMode">
        <template #icon>
          <icon-sun-fill :size="18" v-if="!darkMode" />
          <icon-moon-fill :size="18" v-else />
        </template>
      </a-button>
    </a-tooltip>
    <!-- 全屏 -->
    <a-tooltip :content="$t(`system.${fullScreen ? 'full-screen' : 'exit-full-screen'}`)">
      <a-button size="mini" type="text" class="icon_btn" id="system-fullscreen" @click="onFullScreen">
        <template #icon>
          <icon-fullscreen :size="18" v-if="fullScreen" />
          <icon-fullscreen-exit :size="18" v-else />
        </template>
      </a-button>
    </a-tooltip>
    <!-- 系统设置 -->
    <a-tooltip :content="$t(`system.system-settings`)">
      <a-button size="mini" type="text" class="icon_btn" id="system-settings" @click="onSystemSetting">
        <template #icon>
          <icon-settings :size="18" />
        </template>
      </a-button>
    </a-tooltip>
    <!-- 主题设置 -->
    <a-tooltip :content="$t(`system.theme-settings`)">
      <a-button size="mini" type="text" class="icon_btn" id="system-theme" @click="onThemeSetting">
        <template #icon>
          <icon-skin :size="18" />
        </template>
      </a-button>
    </a-tooltip>
    <!-- 我的 -->
    <a-dropdown trigger="hover">
      <div class="my_setting" id="system-my-setting">
        <a-image width="32" height="32" fit="cover" :src="account.user.avatar_url || account.user.avatar || defaultAvatar" class="my_image" />
        <span class="user-nickname" v-if="!isMobile">{{ account.user.nickName }}</span>
        <div class="icon_down">
          <icon-down style="stroke-width: 3" />
        </div>
      </div>
      <template #content>
        <!-- 个人中心 -->
        <a-doption @click="onPerson(1)">
          <template #default>
            <s-svg-icon :name="'user'" :size="18" />
            <span class="margin-left-text">{{ $t(`system.personal-information`) }}</span>
          </template>
        </a-doption>
        <a-divider margin="0" />
        <!-- 退出登录 -->
        <a-doption @click="logOut">
          <template #default>
            <s-svg-icon :name="'exit'" :size="18" />
            <span class="margin-left-text">{{ $t(`system.logout`) }}</span>
          </template>
        </a-doption>
      </template>
    </a-dropdown>
  </div>
  <SystemSettings :system-open="systemOpen" @system-cancel="systemOpen = false" />
  <ThemeSettings :theme-open="themeOpen" @theme-cancel="themeOpen = false" />
</template>

<script setup lang="ts">
import SystemSettings from "@/layout/components/Header/components/system-settings/index.vue";
import ThemeSettings from "@/layout/components/Header/components/theme-settings/index.vue";
const defaultAvatar = "data:image/webp;base64,UklGRkYFAABXRUJQVlA4IDoFAABQJQCdASqAAIAAPwF0sVSrJiQophQLYWAgCWUAz2RrHxZLF3RFa6+kpqujeA+r2e/TDnHi6kohtoNd0nBYiLvwMYFsFfOhctQWwpuCxA/OuA7tA5+JAZIKZieX5ANDHlKMEoSr+ahXcjvByN2R0Trc+8yyRZnyHCtB1ROyAU+/1xkQaqtG0UgdOcBVOGBEAT4hApLqvNvb0hdzXIQ4kEb8hbzHcm8lsXhKi7ke77+TBp7YZSs5lizE2xA9bM/TwMmtbJMxiBS0G/F8VpTxWNC5bcG8hvWvxwCuvO7j5c/66v0QPFUtye5iduHqYJzJ2UujVYj0q5ybtWBi5vFJdZc0QhSkZLqfqv/nDVaa/TjCiQbIVVk7dOvldikKfOF37vc40/43csHyN4GSdrmX1FaExwAqAP700KW6XfqD9qefqW2PBrjQIChmpCIKLtKhQe/SFQxGRit4HpLGmMmSehO3TZzY7QDu2fbxDhA1ocmgbPdRfsaddj0kBh4jYewFYUmYQADqsGXxUbYdOnSyd8hYshR/YK7nX1MHEp6Wz+dseekJhDfCvFB+YuhUMnd8grcoAO7cfbrIzBPDBOCc+UTyabGImuEfvBRX5hEJdtAAeW3hu/9v90j9YXS6c+3bbkaUEdYMENdzaWibjmXix0lzrPgb/PpI62rQRl5ulBPWCcfkuVPBQQpzM8MB4GOib6XCgBV2JsBv0byKZmVHwhFhunpF2GpCQ7GyVFRGf2wQwTqHJe8iaJxa2UsgmolpYXvgM2iv8Rfbu4YX+QWnkIy3/jfRQeDDxoBU7WvLAinxDvOelDWJmW+i4pZ2qAnu9b8gDHsOpHUHaDEEUsWoIgzsN0jhCHZnjoBZX4BFUNLtdkaH1cc8N4/rnoWbQJKx/C3Aydnq9hY0r6KY0H2FkIRhj/oHShHtGaSE5mCbA+hlOjNcffDJQ2mGXzr/f6Gei/qTHAflzOYt11vLbgyWxUO59MEbgZQnDcto7LqoG9kky462d8g+crZLu8Nvh2pnl/ddO9V4A7KANuTLZj6RMVR9cLb//gNsULl5a7eWyTNi3u2UJC74xqj02zSdQCO3pVSRArCGJLD8dQ1J02Gr0zGzVeZ6a+jpf4LkOqF+QFysjL9gS89D2+9NxpeaK5SAbN5v9yJcuXcBXmIGUWAasVR6H0thz9i/p17vP7FO+++UolAFaAP0eTSqp/hTmuh9N6TZQcnuWEyL7Z4A+l7NETuekqfocmpQywkRk38BY3aqY8N7rWooFHcqRI5pGQD/okC8BGfdwb7wk0JUqlqnuC8fut5V0qO+2fqkTAZsegwzCIKWyULRX0vZrDMW25vR+b/4zihtGUSlasIsQF8YC9DzX9JwX0ZtiYOtQ65qrqS/ca1IuBWbdx8odv+FxhZyr8ag62+pOnmT2SweDWY5MPJCGaWnPXKzW4xkSXA+VSU8P9eea/oz4uCXXw7c0f9/xND+cUvbR/CNMpq4FcomLk1objjDDGEsx+IISM4DQubJhjLdVs6yY7U3q4jaDp50LpYmIagN2oy0ZI1ISKwNVoo1YSGVguiospH06L8lko03ofc0vahPAr/FhQ/crYseBhA+LfSZAI/f9ogmrm/NDUsga+IF7FIvAhV+RGmsWZm8NA8pQvE1WulhuzxCoW/G2npZFwSrM58RUeE83IDj9fdAhQByN4orfB8iNNpP3Qm5wZDG/zlMUekZWverF7ZUY2blGhfh6iOfI6SQPerKvt1Hiau7UrUllkcuffo5wnL8GRc4AuAYrQAAAA==";
import { useI18n } from "vue-i18n";
import { Modal } from "@arco-design/web-vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useUserInfoStore } from "@/store/modules/user-info";
import { useThemeConfig } from "@/store/modules/theme-config";
import { useThemeMethods } from "@/hooks/useThemeMethods";
import { useDevicesSize } from "@/hooks/useDevicesSize";
import { useRouteConfigStore } from "@/store/modules/route-config";

const i18n = useI18n();
const router = useRouter();
const { isMobile } = useDevicesSize();
const userStore = useUserInfoStore();
const themeStore = useThemeConfig();
const { account } = storeToRefs(userStore);
const { language, darkMode } = storeToRefs(themeStore);

// 系统设置
const systemOpen = ref(false);
const onSystemSetting = () => {
  systemOpen.value = true;
};

// 主题设置
const themeOpen = ref(false);
const onThemeSetting = () => {
  themeOpen.value = true;
};
// 全屏
const fullScreen = ref(true);
const onFullScreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
    fullScreen.value = false;
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
      fullScreen.value = true;
    }
  }
};

// 黑暗模式
const onNightMode = () => {
  darkMode.value = !darkMode.value;
  let { setDarkMode } = useThemeMethods();
  setDarkMode();
};

// 语言
const onLange = (value: string) => {
  if (value === "Chinese" || value === "中文") {
    themeStore.setLanguage("zh-CN");
  } else {
    themeStore.setLanguage("en-US");
  }
  i18n.locale.value = language.value;
};

// 个人中心
const onPerson = (type: number) => {
  router.push({
    path: "/system/basic-settings",
    query: {
      id: account.value.user.id,
      userName: account.value.user.userName,
      type
    }
  });
};

// 退出登录
const logOut = () => {
  Modal.warning({
    title: "提示",
    content: "确定退出登录？",
    hideCancel: false,
    closable: true,
    onBeforeOk: async () => {
      try {
        // 用户退出
        await userStore.logOut();
        router.replace("/login");
        // 清除路由数据
        useRouteConfigStore().resetRoute();
        return true;
      } catch {
        return false;
      }
    }
  });
};
</script>

<style lang="scss" scoped>
.head-absolute-fix {
  position: absolute;
  top: 0;
  right: $padding;
}
.header_setting {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  background-color: $color-bg-2;
  > .icon_btn {
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: space-around;
    width: $icon-box;
    height: $icon-box;
    margin-left: $margin;
    color: $color-text-1;
    border-radius: $radius-box-1;
  }
  .my_setting {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 32px;
    margin-left: $margin;
    overflow: hidden;
    .my_image {
      margin-right: 8px;
      border-radius: 50%;
    }
    .user-nickname {
      white-space: nowrap;
    }
    .icon_down {
      margin: 0 0 0 5px;
      transform: rotate(0deg);
      transition: transform 0.2s;
    }
  }
}
:deep(.arco-dropdown-open) {
  .icon_down {
    transform: rotate(180deg) !important;
  }
}
.margin-left-text {
  margin-left: $margin-text;
}
</style>
