<template>
  <a-layout-footer class="footer">
    <div class="footer_title">{{ currentYear }} © TGDrive</div>
  </a-layout-footer>
</template>

<script setup lang="ts">
const currentYear = ref(new Date().getFullYear());
</script>

<style lang="scss" scoped>
.footer {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  height: 30px;
  border-top: $border-1 solid $color-border-2;
}
.footer_title {
  margin: 0 auto;
  color: $color-text-4;
  text-align: center;
}
</style>
