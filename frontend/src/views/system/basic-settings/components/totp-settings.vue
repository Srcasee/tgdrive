<template>
  <a-card title="动态口令（TOTP）" :bordered="false">
    <a-space direction="vertical" size="medium" fill>
      <a-alert type="info">
        动态口令默认关闭。启用后，登录时除账号密码和图形验证码外，还需要输入身份验证器生成的 6 位动态码。
      </a-alert>
      <a-tag :color="enabled ? 'green' : 'gray'">{{ enabled ? "已启用" : "未启用" }}</a-tag>

      <template v-if="!enabled">
        <a-form v-if="!setupInfo" :model="setupForm" layout="vertical" @submit="onSetup">
          <a-form-item field="currentPassword" label="当前密码" required>
            <a-input-password v-model="setupForm.currentPassword" placeholder="验证身份后生成密钥" allow-clear />
          </a-form-item>
          <a-button type="primary" html-type="submit" :loading="busy">开始设置</a-button>
        </a-form>

        <template v-else>
          <a-typography-paragraph>
            在 Google Authenticator、Microsoft Authenticator 或其他支持 TOTP 的应用中，手动添加账户并输入以下密钥：
          </a-typography-paragraph>
          <a-typography-paragraph copyable>{{ setupInfo.secret }}</a-typography-paragraph>
          <a-typography-paragraph>也可以将以下配置地址用于支持 otpauth 的身份验证器：</a-typography-paragraph>
          <a-typography-paragraph copyable>{{ setupInfo.otpauth_url }}</a-typography-paragraph>
          <a-form :model="enableForm" layout="vertical" @submit="onEnable">
            <a-form-item field="code" label="验证应用生成的 6 位动态码" required>
              <a-input v-model="enableForm.code" :max-length="6" placeholder="输入动态口令" allow-clear />
            </a-form-item>
            <a-space>
              <a-button type="primary" html-type="submit" :loading="busy">验证并启用</a-button>
              <a-button :disabled="busy" @click="cancelSetup">取消</a-button>
            </a-space>
          </a-form>
        </template>
      </template>

      <a-form v-else :model="disableForm" layout="vertical" @submit="onDisable">
        <a-form-item field="currentPassword" label="当前密码" required>
          <a-input-password v-model="disableForm.currentPassword" placeholder="关闭动态口令前验证密码" allow-clear />
        </a-form-item>
        <a-form-item field="code" label="当前动态口令" required>
          <a-input v-model="disableForm.code" :max-length="6" placeholder="输入身份验证器中的 6 位代码" allow-clear />
        </a-form-item>
        <a-button status="danger" html-type="submit" :loading="busy">关闭动态口令</a-button>
      </a-form>
    </a-space>
  </a-card>
</template>

<script setup lang="ts">
import useGlobalProperties from "@/hooks/useGlobalProperties";
import { disableTotpAPI, enableTotpAPI, getTotpStatusAPI, setupTotpAPI } from "@/api/modules/user";

const proxy = useGlobalProperties();
const enabled = ref(false);
const busy = ref(false);
const setupInfo = ref<{ secret: string; otpauth_url: string } | null>(null);
const setupForm = ref({ currentPassword: "" });
const enableForm = ref({ code: "" });
const disableForm = ref({ currentPassword: "", code: "" });

const refreshStatus = async () => {
  const result = await getTotpStatusAPI();
  enabled.value = result.data.enabled;
};

const onSetup = async ({ errors }: any) => {
  if (errors || busy.value) return;
  try {
    busy.value = true;
    const result = await setupTotpAPI(setupForm.value.currentPassword);
    setupInfo.value = result.data;
    setupForm.value.currentPassword = "";
    enableForm.value.code = "";
  } catch (error: any) {
    proxy.$message.error(error?.response?.data?.detail || "无法生成动态口令密钥");
  } finally {
    busy.value = false;
  }
};

const onEnable = async ({ errors }: any) => {
  if (errors || busy.value) return;
  try {
    busy.value = true;
    await enableTotpAPI(enableForm.value.code);
    enabled.value = true;
    setupInfo.value = null;
    enableForm.value.code = "";
    proxy.$message.success("动态口令已启用");
  } catch (error: any) {
    proxy.$message.error(error?.response?.data?.detail || "验证失败，请检查动态口令");
  } finally {
    busy.value = false;
  }
};

const cancelSetup = () => {
  setupInfo.value = null;
  enableForm.value.code = "";
};

const onDisable = async ({ errors }: any) => {
  if (errors || busy.value) return;
  try {
    busy.value = true;
    await disableTotpAPI(disableForm.value.currentPassword, disableForm.value.code);
    enabled.value = false;
    disableForm.value = { currentPassword: "", code: "" };
    proxy.$message.success("动态口令已关闭");
  } catch (error: any) {
    proxy.$message.error(error?.response?.data?.detail || "关闭失败，请检查密码和动态口令");
  } finally {
    busy.value = false;
  }
};

void refreshStatus().catch((error: any) => {
  proxy.$message.error(error?.response?.data?.detail || "读取动态口令状态失败");
});
</script>
