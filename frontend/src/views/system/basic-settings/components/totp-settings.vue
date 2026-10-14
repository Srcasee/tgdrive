<template>
  <a-card title="动态口令（TOTP）" :bordered="false">
    <a-space direction="vertical" size="medium" fill>
      <a-alert type="info">
        动态口令默认关闭。启用后，登录时除账号密码和图形验证码外，还需要输入身份验证器生成的 6 位动态码。
      </a-alert>
      <a-descriptions :column="1" bordered>
        <a-descriptions-item label="当前状态">
          <a-tag :color="enabled ? 'green' : 'gray'">{{ enabled ? "已启用" : "未启用" }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="支持验证器">
          Google Authenticator、Microsoft Authenticator 等
        </a-descriptions-item>
      </a-descriptions>
      <p v-if="!enabled">启用后，登录时需要输入验证器生成的 6 位动态口令。</p>
      <a-button v-if="!enabled" type="primary" @click="openSetup">启用动态口令</a-button>
      <a-button v-else status="danger" @click="openDisable">关闭动态口令</a-button>
    </a-space>
  </a-card>

  <a-modal
    v-model:visible="passwordModalVisible"
    title="启用动态口令 · 验证身份"
    :mask-closable="false"
    :footer="false"
    @cancel="resetSetup"
  >
    <a-form :model="setupForm" layout="vertical" @submit="onSetup">
      <a-form-item field="currentPassword" label="当前登录密码" required>
        <a-input-password v-model="setupForm.currentPassword" placeholder="请输入当前登录密码" allow-clear />
      </a-form-item>
      <p class="modal-hint">为确认是本人操作，需要校验当前登录密码。</p>
      <div class="modal-actions">
        <a-button @click="passwordModalVisible = false">取消</a-button>
        <a-button type="primary" html-type="submit" :loading="busy">下一步</a-button>
      </div>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="bindingModalVisible"
    title="启用动态口令 · 绑定验证器"
    :mask-closable="false"
    :footer="false"
    @cancel="resetSetup"
  >
    <a-alert type="info" class="binding-hint">
      请使用验证器扫描二维码或手动录入下方密钥，然后输入验证器生成的 6 位动态口令完成绑定。
    </a-alert>
    <div class="qr-wrap">
      <img v-if="qrCodeUrl" :src="qrCodeUrl" alt="动态口令绑定二维码" class="qr-code" />
    </div>
    <div class="secret-box">
      <div class="field-label">密钥（手动录入）</div>
      <a-typography-paragraph copyable>{{ setupInfo?.secret }}</a-typography-paragraph>
    </div>
    <a-form :model="enableForm" layout="vertical" @submit="onEnable">
      <a-form-item field="code" label="动态口令" required>
        <a-input
          v-model="enableForm.code"
          :max-length="6"
          placeholder="请输入 6 位动态口令"
          allow-clear
        />
      </a-form-item>
      <div class="modal-actions">
        <a-button :disabled="busy" @click="resetSetup">取消</a-button>
        <a-button type="primary" html-type="submit" :loading="busy">确认启用</a-button>
      </div>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="disableModalVisible"
    title="关闭动态口令 · 验证身份"
    :mask-closable="false"
    :footer="false"
  >
    <a-form :model="disableForm" layout="vertical" @submit="onDisable">
      <a-form-item field="currentPassword" label="当前登录密码" required>
        <a-input-password v-model="disableForm.currentPassword" placeholder="请输入当前登录密码" allow-clear />
      </a-form-item>
      <a-form-item field="code" label="当前动态口令" required>
        <a-input v-model="disableForm.code" :max-length="6" placeholder="请输入验证器生成的 6 位代码" allow-clear />
      </a-form-item>
      <div class="modal-actions">
        <a-button @click="disableModalVisible = false">取消</a-button>
        <a-button status="danger" type="primary" html-type="submit" :loading="busy">确认关闭</a-button>
      </div>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import QRCode from "qrcode";
import useGlobalProperties from "@/hooks/useGlobalProperties";
import { disableTotpAPI, enableTotpAPI, getTotpStatusAPI, setupTotpAPI } from "@/api/modules/user";

const proxy = useGlobalProperties();
const enabled = ref(false);
const busy = ref(false);
const passwordModalVisible = ref(false);
const bindingModalVisible = ref(false);
const disableModalVisible = ref(false);
const setupInfo = ref<{ secret: string; otpauth_url: string } | null>(null);
const qrCodeUrl = ref("");
const setupForm = ref({ currentPassword: "" });
const enableForm = ref({ code: "" });
const disableForm = ref({ currentPassword: "", code: "" });

const refreshStatus = async () => {
  const result = await getTotpStatusAPI();
  enabled.value = result.data.enabled;
};

const openSetup = () => {
  setupForm.value.currentPassword = "";
  passwordModalVisible.value = true;
};

const onSetup = async ({ errors }: any) => {
  if (errors || busy.value) return;
  try {
    busy.value = true;
    const result = await setupTotpAPI(setupForm.value.currentPassword);
    setupInfo.value = result.data;
    qrCodeUrl.value = await QRCode.toDataURL(result.data.otpauth_url, {
      width: 220,
      margin: 2,
      errorCorrectionLevel: "M"
    });
    setupForm.value.currentPassword = "";
    enableForm.value.code = "";
    passwordModalVisible.value = false;
    bindingModalVisible.value = true;
  } catch (error: any) {
    proxy.$message.error(error?.response?.data?.detail || "无法生成动态口令密钥或二维码");
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
    bindingModalVisible.value = false;
    setupInfo.value = null;
    qrCodeUrl.value = "";
    enableForm.value.code = "";
    proxy.$message.success("动态口令已启用");
  } catch (error: any) {
    proxy.$message.error(error?.response?.data?.detail || "验证失败，请检查动态口令");
  } finally {
    busy.value = false;
  }
};

const resetSetup = () => {
  passwordModalVisible.value = false;
  bindingModalVisible.value = false;
  setupInfo.value = null;
  qrCodeUrl.value = "";
  setupForm.value.currentPassword = "";
  enableForm.value.code = "";
};

const openDisable = () => {
  disableForm.value = { currentPassword: "", code: "" };
  disableModalVisible.value = true;
};

const onDisable = async ({ errors }: any) => {
  if (errors || busy.value) return;
  try {
    busy.value = true;
    await disableTotpAPI(disableForm.value.currentPassword, disableForm.value.code);
    enabled.value = false;
    disableModalVisible.value = false;
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

<style scoped lang="scss">
.modal-hint {
  color: var(--color-text-3);
  margin: 12px 0 20px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
.binding-hint {
  margin-bottom: 16px;
}
.qr-wrap {
  display: flex;
  justify-content: center;
  padding: 8px 0 18px;
}
.qr-code {
  width: 220px;
  height: 220px;
  image-rendering: pixelated;
}
.secret-box {
  padding: 12px 16px 4px;
  margin-bottom: 16px;
  border: 1px solid var(--color-border-2);
  border-radius: 6px;
  overflow-wrap: anywhere;
}
.field-label {
  margin-bottom: 8px;
  color: var(--color-text-3);
  font-size: 13px;
}
</style>
