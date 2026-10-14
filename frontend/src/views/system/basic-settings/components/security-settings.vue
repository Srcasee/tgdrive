<template>
  <a-row align="center" :gutter="[0, 16]">
    <a-col :span="24">
      <a-card title="安全设置">
        <a-form :model="form" :rules="rules" :layout="layoutMode" :style="{ maxWidth: '600px' }" @submit="onSubmit">
          <a-form-item field="username" label="账号">
            <a-input v-model="form.username" placeholder="请输入新账号" allow-clear />
          </a-form-item>
          <a-form-item field="currentPassword" label="当前密码">
            <a-input-password v-model="form.currentPassword" placeholder="修改账号或密码时请输入当前密码" allow-clear />
          </a-form-item>
          <a-form-item field="newPassword" label="新密码">
            <a-input-password v-model="form.newPassword" placeholder="不修改密码请留空，至少 8 位" allow-clear />
          </a-form-item>
          <a-form-item field="confirmPassword" label="确认新密码">
            <a-input-password v-model="form.confirmPassword" placeholder="再次输入新密码" allow-clear />
          </a-form-item>
          <a-form-item>
            <a-button type="primary" html-type="submit" :loading="saving">保存修改</a-button>
          </a-form-item>
        </a-form>
      </a-card>
    </a-col>
  </a-row>
</template>

<script setup lang="ts">
import useGlobalProperties from "@/hooks/useGlobalProperties";
import { useDevicesSize } from "@/hooks/useDevicesSize";
import { updateUserProfileAPI } from "@/api/modules/user";

const emit = defineEmits(["refresh"]);
const proxy = useGlobalProperties();
const data = defineModel() as any;
const { isMobile } = useDevicesSize();
const layoutMode = computed(() => (isMobile.value ? "vertical" : "horizontal"));
const saving = ref(false);
const form = ref({
  username: "",
  currentPassword: "",
  newPassword: "",
  confirmPassword: ""
});
const rules = {
  username: [
    { required: true, message: "账号不能为空" },
    { minLength: 3, message: "账号至少 3 个字符" }
  ],
  currentPassword: [{ required: true, message: "请输入当前密码" }]
};

watch(
  () => data.value?.username,
  username => {
    form.value.username = username || "";
  },
  { immediate: true }
);

const onSubmit = async ({ errors }: ArcoDesign.ArcoSubmit) => {
  if (errors || saving.value) return;
  if (form.value.newPassword && form.value.newPassword.length < 8) {
    proxy.$message.warning("新密码至少需要 8 位");
    return;
  }
  if (form.value.newPassword !== form.value.confirmPassword) {
    proxy.$message.warning("两次输入的新密码不一致");
    return;
  }

  try {
    saving.value = true;
    const result = await updateUserProfileAPI({
      username: form.value.username.trim(),
      current_password: form.value.currentPassword,
      new_password: form.value.newPassword || null
    });
    data.value = { ...data.value, ...result.data };
    form.value.currentPassword = "";
    form.value.newPassword = "";
    form.value.confirmPassword = "";
    proxy.$message.success("账号信息已更新");
    emit("refresh");
  } catch (error: any) {
    proxy.$message.error(error?.response?.data?.detail || "修改失败，请检查当前密码后重试");
  } finally {
    saving.value = false;
  }
};
</script>
