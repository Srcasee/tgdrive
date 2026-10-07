<template>
  <div class="snow-page">
    <div class="snow-inner">
      <a-space direction="vertical" fill size="large">
        <a-row justify="end">
          <a-space>
            <a-button @click="openRestore">恢复</a-button>
            <a-button type="primary" @click="openLogin">
              <template #icon><icon-plus /></template>
              <span>新增</span>
            </a-button>
          </a-space>
        </a-row>

        <a-table :data="rows" :loading="loading" row-key="id" :bordered="{ cell: true }">
          <template #columns>
            <a-table-column title="ID" :width="80"><template #cell="{ rowIndex }">{{ rowIndex + 1 }}</template></a-table-column>
            <a-table-column title="登录名" data-index="login_name" :width="160" ellipsis tooltip />
            <a-table-column title="昵称" data-index="nickname" :width="160" ellipsis tooltip />
            <a-table-column title="用户名" data-index="telegram_username" :width="160" ellipsis tooltip>
              <template #cell="{ record }">{{ record.telegram_username ? `@${record.telegram_username}` : "-" }}</template>
            </a-table-column>
            <a-table-column title="Telegram ID" data-index="telegram_user_id" :width="140" />
            <a-table-column title="手机号" data-index="telegram_phone" :width="140" />
            <a-table-column title="状态" :width="90" align="center">
              <template #cell="{ record }">
                <a-tag bordered size="small" :color="record.authorized === false ? 'red' : 'arcoblue'">
                  {{ record.authorized === false ? "未登录" : record.enabled ? "启用" : "禁用" }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" :width="180" align="center">
              <template #cell="{ record }">
                <a-space>
                  <a-button type="primary" size="mini" @click="openEdit(record)">
                    <template #icon><icon-edit /></template>
                    <span>编辑</span>
                  </a-button>
                  <a-popconfirm type="warning" content="删除账号信息，但保留已经生成的 session 文件，确定继续吗？" @ok="remove(record)">
                    <a-button type="primary" status="danger" size="mini">
                      <template #icon><icon-delete /></template>
                      <span>删除</span>
                    </a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-space>
    </div>

    <a-modal v-model:visible="restoreVisible" :width="520" :mask-closable="false" :footer="false">
      <template #title>恢复账号</template>
      <a-table :data="deletedSessions" :loading="restoreLoading" :pagination="false" row-key="session">
        <template #columns>
          <a-table-column title="Session" data-index="session" ellipsis tooltip />
          <a-table-column title="操作" :width="90" align="center">
            <template #cell="{ record }">
              <a-button type="primary" size="mini" @click="restore(record.session)">恢复</a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-modal>

    <a-modal v-model:visible="editVisible" :width="620" :mask-closable="false" :footer="false">
      <template #title>编辑 Telegram 账号</template>
      <a-space direction="vertical" fill size="medium">
        <a-descriptions :column="1" bordered>
          <a-descriptions-item label="登录名"><a-space fill><span>{{ editForm.login_name }}</span><a-button type="text" size="mini" @click="editField('login_name')">更改</a-button></a-space></a-descriptions-item>
          <a-descriptions-item label="昵称"><a-space fill><span>{{ editForm.nickname || "-" }}</span><a-button type="text" size="mini" @click="editField('nickname')">更改</a-button></a-space></a-descriptions-item>
          <a-descriptions-item label="用户名"><a-space fill><span>{{ editForm.telegram_username ? `@${editForm.telegram_username}` : "-" }}</span><a-button type="text" size="mini" @click="editField('username')">更改</a-button></a-space></a-descriptions-item>
          <a-descriptions-item label="手机号"><a-space fill><span>{{ editForm.telegram_phone || "-" }}</span><a-button type="text" size="mini" @click="editPhone">更改</a-button></a-space></a-descriptions-item>
          <a-descriptions-item label="登录邮箱"><a-space fill><span>{{ editForm.login_email || "Telegram 不提供现有登录邮箱读取接口" }}</span><a-button type="text" size="mini" @click="editLoginEmail">更改</a-button></a-space></a-descriptions-item>
        </a-descriptions>
        <a-alert type="info">这里的“登录邮箱”是 Telegram 用于接收登录验证码的邮箱，与 2FA 恢复邮箱不是同一个字段。</a-alert>
      </a-space>
    </a-modal>

    <a-modal v-model:visible="fieldVisible" :width="480" :mask-closable="false" :footer="false">
      <template #title>更改{{ fieldTitle }}</template>
      <a-form :model="fieldForm" auto-label-width>
        <a-form-item :label="fieldTitle"><a-input v-model="fieldForm.value" allow-clear /></a-form-item>
        <a-space fill justify="end"><a-button @click="fieldVisible = false">取消</a-button><a-button type="primary" :loading="editLoading" @click="saveField">保存</a-button></a-space>
      </a-form>
    </a-modal>

    <a-modal v-model:visible="emailVisible" :width="480" :mask-closable="false" :footer="false">
      <template #title>更改登录邮箱</template>
      <a-form v-if="!emailCodeRequired" :model="emailForm" auto-label-width>
        <a-form-item label="新邮箱"><a-input v-model="emailForm.email" allow-clear placeholder="请输入新的 Telegram 登录邮箱" /></a-form-item>
        <a-space fill justify="end"><a-button @click="emailVisible = false">取消</a-button><a-button type="primary" :loading="editLoading" @click="startEmailEdit">发送验证邮件</a-button></a-space>
      </a-form>
      <a-form v-else :model="emailForm" auto-label-width>
        <a-form-item label="邮箱验证码"><a-input v-model="emailForm.code" allow-clear /></a-form-item>
        <a-space fill justify="end"><a-button @click="emailVisible = false">取消</a-button><a-button type="primary" :loading="editLoading" @click="confirmEmailEdit">确认修改</a-button></a-space>
      </a-form>
    </a-modal>

    <a-modal v-model:visible="phoneVisible" :width="480" :mask-closable="false" :footer="false">
      <template #title>更改手机号</template>
      <a-form v-if="!phoneCodeRequired" :model="phoneForm" auto-label-width>
        <a-form-item label="新手机号"><a-input v-model="phoneForm.phone" allow-clear /></a-form-item>
        <a-space fill justify="end"><a-button @click="phoneVisible = false">取消</a-button><a-button type="primary" :loading="editLoading" @click="startPhoneEdit">发送验证码</a-button></a-space>
      </a-form>
      <a-form v-else :model="phoneForm" auto-label-width>
        <a-form-item label="验证码"><a-input v-model="phoneForm.code" allow-clear /></a-form-item>
        <a-space fill justify="end"><a-button @click="phoneVisible = false">取消</a-button><a-button type="primary" :loading="editLoading" @click="confirmPhoneEdit">确认修改</a-button></a-space>
      </a-form>
    </a-modal>

    <a-modal
      v-model:visible="loginVisible"
      :width="520"
      :mask-closable="false"
      :closable="loginStep === 'start'"
      :footer="false"
      @cancel="cancelLogin"
    >
      <template #title>新增 Telegram 账号</template>

      <a-steps :current="loginStepIndex" size="small" class="steps">
        <a-step>账号信息</a-step>
        <a-step>验证码</a-step>
        <a-step v-if="loginStep === 'password' || loginStep === 'success'">两步验证</a-step>
      </a-steps>

      <a-form v-if="loginStep === 'start'" ref="startFormRef" :model="loginForm" :rules="startRules" auto-label-width>
        <a-form-item field="login_name" label="登录名">
          <a-input v-model="loginForm.login_name" placeholder="例如：account_01" allow-clear />
        </a-form-item>
        <a-form-item field="phone" label="手机号">
          <a-input v-model="loginForm.phone" placeholder="例如：+8613812345678" allow-clear />
        </a-form-item>
        <a-space fill justify="end">
          <a-button @click="cancelLogin">取消</a-button>
          <a-button type="primary" :loading="loginLoading" @click="startLogin">开始登录</a-button>
        </a-space>
      </a-form>

      <a-form v-else-if="loginStep === 'code'" ref="codeFormRef" :model="codeForm" :rules="codeRules" auto-label-width>
        <a-alert class="alert" type="info">验证码已发送到 Telegram，请输入收到的验证码。</a-alert>
        <a-form-item field="code" label="验证码">
          <a-input v-model="codeForm.code" placeholder="请输入验证码" allow-clear />
        </a-form-item>
        <a-space fill justify="end">
          <a-button :disabled="loginLoading" @click="cancelLogin">取消</a-button>
          <a-button type="primary" :loading="loginLoading" @click="submitCode">验证并继续</a-button>
        </a-space>
      </a-form>

      <a-form v-else-if="loginStep === 'password'" ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" auto-label-width>
        <a-alert class="alert" type="warning">该 Telegram 账号开启了两步验证，请输入 Telegram 密码。</a-alert>
        <a-form-item field="password" label="Telegram 密码">
          <a-input-password v-model="passwordForm.password" placeholder="请输入两步验证密码" allow-clear />
        </a-form-item>
        <a-space fill justify="end">
          <a-button :disabled="loginLoading" @click="cancelLogin">取消</a-button>
          <a-button type="primary" :loading="loginLoading" @click="submitPassword">完成登录</a-button>
        </a-space>
      </a-form>

      <div v-else class="success-state">
        <a-result status="success" title="登录成功" :subtitle="loginMessage" />
        <a-space fill justify="end">
          <a-button type="primary" @click="finishLogin">完成</a-button>
        </a-space>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Message } from "@arco-design/web-vue";
import {
  getAccountsAPI,
  deleteAccountAPI,
  getDeletedAccountsAPI,
  restoreDeletedAccountAPI,
  updateAccountProfileAPI,
  startAccountPhoneChangeAPI,
  confirmAccountPhoneChangeAPI,
  startAccountEmailChangeAPI,
  confirmAccountEmailChangeAPI,
  startAccountLoginAPI,
  submitAccountLoginCodeAPI,
  submitAccountLoginPasswordAPI,
  cancelAccountLoginAPI
} from "@/api/modules/tgdrive";

type LoginStep = "start" | "code" | "password" | "success";

const rows = ref<any[]>([]);
const loading = ref(false);
const loginVisible = ref(false);
const loginLoading = ref(false);
const loginStep = ref<LoginStep>("start");
const loginId = ref("");
const loginMessage = ref("");
const editVisible = ref(false);
const fieldVisible = ref(false);
const phoneVisible = ref(false);
const emailVisible = ref(false);
const editLoading = ref(false);
const restoreVisible = ref(false);
const restoreLoading = ref(false);
const deletedSessions = ref<string[]>([]);
const editRow = ref<any>(null);
const editForm = ref<any>({});
const fieldName = ref<"login_name" | "nickname" | "username">("nickname");
const fieldForm = ref({ value: "" });
const phoneForm = ref({ phone: "", code: "" });
const phoneCodeRequired = ref(false);
const emailForm = ref({ email: "", code: "" });
const emailCodeRequired = ref(false);
const fieldTitle = computed(() => ({ login_name: "登录名", nickname: "昵称", username: "用户名" }[fieldName.value]));

const loginStepIndex = computed(() => {
  if (loginStep.value === "start") return 1;
  if (loginStep.value === "code") return 2;
  return 3;
});

const loginForm = ref({ login_name: "", phone: "" });
const codeForm = ref({ code: "" });
const passwordForm = ref({ password: "" });
const startFormRef = ref();
const codeFormRef = ref();
const passwordFormRef = ref();

const startRules = {
  login_name: [{ required: true, message: "请输入登录名" }],
  phone: [{ required: true, message: "请输入手机号" }]
};
const codeRules = {
  code: [{ required: true, message: "请输入 Telegram 验证码" }]
};
const passwordRules = {
  password: [{ required: true, message: "请输入 Telegram 两步验证密码" }]
};

const load = async () => {
  loading.value = true;
  try {
    rows.value = (await getAccountsAPI()).data || [];
  } finally {
    loading.value = false;
  }
};

const openRestore = async () => {
  restoreVisible.value = true;
  restoreLoading.value = true;
  try {
    deletedSessions.value = (await getDeletedAccountsAPI()).data || [];
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "获取可恢复账号失败");
  } finally {
    restoreLoading.value = false;
  }
};

const restore = async (session: string) => {
  restoreLoading.value = true;
  try {
    await restoreDeletedAccountAPI(session);
    deletedSessions.value = deletedSessions.value.filter(item => item !== session);
    await load();
    Message.success("账号已恢复");
    if (!deletedSessions.value.length) restoreVisible.value = false;
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "恢复账号失败");
  } finally {
    restoreLoading.value = false;
  }
};

const openEdit = (row: any) => {
  editRow.value = row;
  editForm.value = { ...row };
  editVisible.value = true;
};

const editField = (name: "login_name" | "nickname" | "username") => {
  fieldName.value = name;
  fieldForm.value.value = fieldName.value === "username"
    ? editForm.value.telegram_username || ""
    : editForm.value[fieldName.value] || "";
  fieldVisible.value = true;
};

const saveField = async () => {
  const value = fieldForm.value.value.trim();
  if (!editRow.value || !value) {
    Message.error("请输入修改内容");
    return;
  }
  editLoading.value = true;
  try {
    const payload: any = {};
    payload[fieldName.value] = value;
    const data = (await updateAccountProfileAPI(editRow.value.id, payload)).data;
    Object.assign(editRow.value, data);
    editForm.value = { ...editForm.value, ...data };
    fieldVisible.value = false;
    Message.success("修改成功");
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "修改失败");
  } finally {
    editLoading.value = false;
  }
};

const editLoginEmail = () => {
  emailForm.value = { email: "", code: "" };
  emailCodeRequired.value = false;
  emailVisible.value = true;
};

const startEmailEdit = async () => {
  if (!emailForm.value.email.trim()) {
    Message.error("请输入新的登录邮箱");
    return;
  }
  editLoading.value = true;
  try {
    const data = (await startAccountEmailChangeAPI(editRow.value.id, emailForm.value.email.trim())).data;
    emailForm.value.email = data.email || emailForm.value.email;
    emailCodeRequired.value = true;
    Message.success("验证邮件已发送");
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "发送验证邮件失败");
  } finally {
    editLoading.value = false;
  }
};

const confirmEmailEdit = async () => {
  if (!emailForm.value.code.trim()) {
    Message.error("请输入邮箱验证码");
    return;
  }
  editLoading.value = true;
  try {
    const data = (await confirmAccountEmailChangeAPI(editRow.value.id, emailForm.value.code.trim())).data;
    editRow.value.login_email = data.email;
    editForm.value.login_email = data.email;
    emailVisible.value = false;
    Message.success("登录邮箱修改成功");
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "修改登录邮箱失败");
  } finally {
    editLoading.value = false;
  }
};

const editPhone = () => {
  phoneForm.value = { phone: "", code: "" };
  phoneCodeRequired.value = false;
  phoneVisible.value = true;
};

const startPhoneEdit = async () => {
  if (!phoneForm.value.phone.trim()) {
    Message.error("请输入新的手机号");
    return;
  }
  editLoading.value = true;
  try {
    await startAccountPhoneChangeAPI(editRow.value.id, phoneForm.value.phone.trim());
    phoneCodeRequired.value = true;
    Message.success("验证码已发送");
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "发送验证码失败");
  } finally {
    editLoading.value = false;
  }
};

const confirmPhoneEdit = async () => {
  if (!phoneForm.value.code.trim()) {
    Message.error("请输入验证码");
    return;
  }
  editLoading.value = true;
  try {
    const data = (await confirmAccountPhoneChangeAPI(editRow.value.id, phoneForm.value.code.trim())).data;
    editRow.value.telegram_phone = data.phone;
    editForm.value.telegram_phone = data.phone;
    phoneVisible.value = false;
    Message.success("手机号修改成功");
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "修改手机号失败");
  } finally {
    editLoading.value = false;
  }
};

const remove = async (row: any) => {
  try {
    await deleteAccountAPI(row.id);
    Message.success("账号信息已删除，session 已保留");
    await load();
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "删除失败");
  }
};

const openLogin = () => {
  loginVisible.value = true;
  loginStep.value = "start";
  loginId.value = "";
  loginMessage.value = "";
  loginForm.value = { login_name: "", phone: "" };
  codeForm.value = { code: "" };
  passwordForm.value = { password: "" };
};

const startLogin = async () => {
  const state = await startFormRef.value.validate();
  if (state) return;

  loginLoading.value = true;
  try {
    const data = (await startAccountLoginAPI(loginForm.value)).data;
    loginId.value = data.id;
    loginStep.value = data.needs_code ? "code" : data.needs_password ? "password" : "success";
    loginMessage.value = data.message || "";
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "启动 Telegram 登录失败");
  } finally {
    loginLoading.value = false;
  }
};

const submitCode = async () => {
  const state = await codeFormRef.value.validate();
  if (state) return;

  loginLoading.value = true;
  try {
    const data = (await submitAccountLoginCodeAPI({ login_id: loginId.value, code: codeForm.value.code })).data;
    if (data.needs_password) {
      loginStep.value = "password";
      loginMessage.value = data.message || "";
    } else {
      loginStep.value = "success";
      loginMessage.value = data.message || "Telegram 登录成功";
    }
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "验证码验证失败");
  } finally {
    loginLoading.value = false;
  }
};

const submitPassword = async () => {
  const state = await passwordFormRef.value.validate();
  if (state) return;

  loginLoading.value = true;
  try {
    const data = (await submitAccountLoginPasswordAPI({ login_id: loginId.value, password: passwordForm.value.password })).data;
    loginStep.value = "success";
    loginMessage.value = data.message || "Telegram 登录成功";
  } catch (error: any) {
    Message.error(error?.response?.data?.detail || "两步验证失败");
  } finally {
    loginLoading.value = false;
  }
};

const cancelLogin = async () => {
  if (loginId.value) {
    try {
      await cancelAccountLoginAPI(loginId.value);
    } catch {
      // 登录流程已经失效时无需阻塞关闭弹窗。
    }
  }
  loginVisible.value = false;
  loginStep.value = "start";
  loginId.value = "";
};

const finishLogin = async () => {
  loginVisible.value = false;
  loginStep.value = "start";
  loginId.value = "";
  await load();
  Message.success("账号已加入账号管理");
};

load();
</script>

<style scoped>
.steps {
  margin-bottom: 28px;
}

.alert {
  margin-bottom: 20px;
}

.success-state {
  padding: 8px 0;
}
</style>
