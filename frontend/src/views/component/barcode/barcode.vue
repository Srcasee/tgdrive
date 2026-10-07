<template>
  <div class="snow-page">
    <div class="snow-inner container">
      <div class="code-box">
        <a-card
          v-for="item in codeList"
          :key="item.id"
          :title="item.docs"
          :style="{ width: isMobile ? '300px' : '400px' }"
          hoverable
        >
          <div class="card-content">
            <s-barcode-draw :tag="item.tag" :text="item.text" :options="item.options" />
          </div>
        </a-card>
      </div>

      <a-scrollbar style="height: 625px; overflow: auto" outer-class="scrollbar">
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
    tag: "svg",
    text: "SnowAdmin",
    docs: "CODE128-默认条形码",
    options: {
      format: "CODE128",
      height: 100
    }
  },
  {
    id: 2,
    tag: "svg",
    text: "SnowAdmin",
    docs: "自定义高度和颜色",
    options: {
      format: "CODE128",
      height: 50,
      background: "#f7f8fa",
      lineColor: "#2962ff"
    }
  },
  {
    id: 3,
    tag: "svg",
    text: "SnowAdmin",
    docs: "设置字体和倾斜",
    options: {
      format: "CODE128",
      height: 100,
      font: "fantasy",
      fontOptions: "italic"
    }
  },
  {
    id: 4,
    tag: "svg",
    text: "SnowAdmin",
    docs: "CODE39-商品条形码",
    options: {
      format: "CODE39",
      height: 100
    }
  },
  {
    id: 5,
    tag: "svg",
    text: "6971318501227",
    docs: "EAN13-商品条形码",
    options: {
      format: "EAN13",
      height: 100
    }
  },
  {
    id: 6,
    tag: "svg",
    text: "123456789999",
    docs: "UPC-商品条形码",
    options: {
      format: "UPC",
      height: 100
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
