<template>
  <div class="snow-page">
    <div class="snow-inner container">
      <div class="code-box">
        <a-card v-for="item in codeList" :key="item.id" :title="item.docs" :style="{ width: '300px' }" hoverable>
          <div class="card-content">
            <s-qrcode-draw :tag="item.tag" :text="item.text" :options="item.options" />
          </div>
        </a-card>
      </div>

      <a-scrollbar style="height: 410px; overflow: auto" outer-class="scrollbar">
        <s-code-view :code-json="codeJson" style="width: 100%" />
      </a-scrollbar>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDevicesSize } from "@/hooks/useDevicesSize";

const { isMobile } = useDevicesSize();
const gradColumns = computed(() => (isMobile.value ? 1 : 2));
const codeWidth = computed(() => (isMobile.value ? "100%" : "500px"));
const codeList = ref([
  {
    id: 1,
    text: "https://gitee.com/wang_fan_w/SnowAdmin",
    docs: "img格式",
    tag: "img",
    options: {
      width: 100, // 二维码的宽度
      height: 100, // 二维码的高度
      color: {
        dark: "#000000", // 二维码的前景色（黑色）
        light: "#ffffff" // 二维码的背景色（白色）
      },
      margin: 4, // 边距，默认是 4
      scale: 4, // 模块大小，默认是 4
      errorCorrectionLevel: "H" // 错误修正级别：L (低), M (中), Q (较高), H (最高)
    }
  },
  {
    id: 2,
    text: "https://gitee.com/wang_fan_w/SnowAdmin",
    docs: "自定义大小和颜色",
    tag: "img",
    options: {
      width: 80, // 二维码的宽度
      height: 80, // 二维码的高度
      color: {
        dark: "#2962ff", // 二维码的前景色（黑色）
        light: "#f7f8fa" // 二维码的背景色（白色）
      },
      margin: 4, // 边距，默认是 4
      scale: 4, // 模块大小，默认是 4
      errorCorrectionLevel: "H" // 错误修正级别：L (低), M (中), Q (较高), H (最高)
    }
  },
  {
    id: 3,
    text: "https://gitee.com/wang_fan_w/SnowAdmin",
    docs: "canvas格式",
    tag: "canvas",
    options: {
      width: 100, // 二维码的宽度
      height: 100, // 二维码的高度
      color: {
        dark: "#000000", // 二维码的前景色（黑色）
        light: "#ffffff" // 二维码的背景色（白色）
      },
      margin: 4, // 边距，默认是 4
      scale: 4, // 模块大小，默认是 4
      errorCorrectionLevel: "H" // 错误修正级别：L (低), M (中), Q (较高), H (最高)
    }
  },
  {
    id: 4,
    text: "https://gitee.com/wang_fan_w/SnowAdmin",
    docs: "高清晰度",
    tag: "img",
    options: {
      width: 100, // 二维码的宽度
      height: 100, // 二维码的高度
      color: {
        dark: "#000000", // 二维码的前景色（黑色）
        light: "#ffffff" // 二维码的背景色（白色）
      },
      margin: 4, // 边距，默认是 4
      scale: 4, // 模块大小，默认是 4
      quality: 1, // 质量，默认0.92
      errorCorrectionLevel: "H" // 错误修正级别：L (低), M (中), Q (较高), H (最高)
    }
  }
]);

const codeJson = computed(() => JSON.stringify(codeList.value, null, "\t"));
</script>

<style lang="scss" scoped>
.container {
  display: flex;
  flex-wrap: wrap;
  gap: $padding;
}
.code-box {
  display: grid;
  grid-template-columns: repeat(v-bind(gradColumns), 1fr);
  gap: $padding $padding;
  .card-content {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 120px;
  }
}
.scrollbar {
  width: v-bind(codeWidth);
  height: 100%;
}
</style>
