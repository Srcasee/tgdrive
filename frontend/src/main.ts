import { createApp } from "vue";
import { createPinia } from "pinia";
import ArcoVue from "@arco-design/web-vue";
import ArcoVueIcon from "@arco-design/web-vue/es/icon";
import "@arco-design/web-vue/dist/arco.css";
import "./style.css";
import App from "./App.vue";
createApp(App).use(createPinia()).use(ArcoVue).use(ArcoVueIcon).mount("#app");