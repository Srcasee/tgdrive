import axios from "axios";
import router from "@/router";
import { Message } from "@arco-design/web-vue";

const MOCK_FLAG = import.meta.env.VITE_APP_OPEN_MOCK === "true";
const service = axios.create({ baseURL: MOCK_FLAG ? "" : "/api", withCredentials: true });

service.interceptors.request.use((config: any) => {
  let userInfo: any = {};
  if (localStorage.getItem("user-info")) {
    userInfo = JSON.parse(localStorage.getItem("user-info") as string);
  }
  if (userInfo?.token && userInfo.token !== "cookie") {
    config.headers.Authorization = userInfo.token;
  }
  return config;
});

service.interceptors.response.use(
  (response: any) => {
    if (response.status !== 200) {
      Message.error("服务器异常，请联系管理员");
      return Promise.reject(response.data);
    }
    const res = response.data;
    if (res?.code === 401) {
      Message.error("登录状态已过期");
      router.push("/login");
      return Promise.reject(res);
    }
    if (res?.code && res.code !== 200) {
      Message.error(res.message);
      return Promise.reject(res);
    }
    return Promise.resolve(res);
  },
  (error: any) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("user-info");
      router.push("/login");
    }
    return Promise.reject(error);
  }
);

export default service;
