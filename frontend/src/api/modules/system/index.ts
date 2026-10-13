import { deepClone, buildTreeOptimized, filterByDisable, treeSort } from "@/mock/_utils";
import { systemMenu, permissionData } from "@/mock/_data/system_menu";
import axios from "@/api";

// 获取菜单数据
// 菜单管理与动态路由共用同一份持久化配置，避免“管理页改了，但侧边栏仍使用旧 mock 数据”。
// 从历史本地菜单配置中清理已移除的模板导航，避免旧缓存重新生成这些路由。
const DELETED_NAVIGATION_PATHS = [
  "/component",
  "/home",
  "/file",
  "/multilevel",
  "/functions",
  "/permission",
  "/link",
  "/monitor",
  "/disable-menu",
  "/hide-menu",
  "/system/log",
  "/component/print",
  "/component/draggable",
  "/component/editor",
  "/component/newbie",
  "/component/icon-selector",
  "/component/user-center",
  "/component/barcode",
  "/component/qrcode",
  "/component/pinyin",
  "/component/recorder",
  "/component/virtual-list",
  "/component/common-layouts",
  "/system/account",
  "/system/division",
  "/system/dictionary"
];

const removeDeletedNavigationEntries = (nodes: any[]): any[] =>
  nodes
    .filter(node => !DELETED_NAVIGATION_PATHS.some(path => node.path === path || node.path?.startsWith(path + "/")))
    .map(node => ({
      ...node,
      children: node.children?.length ? removeDeletedNavigationEntries(node.children) : node.children
    }));

// 历史 localStorage 菜单可能早于 TGDrive 页面，补齐默认 TGDrive 路由，避免登录后 HOME_PATH 指向不存在的动态路由。
const mergeRequiredNavigationEntries = (nodes: any[]): any[] => {
  const merged = nodes.map(node => ({
    ...node,
    children: node.children?.length ? mergeRequiredNavigationEntries(node.children) : node.children
  }));
  const existingPaths = new Set<string>();
  const collectPaths = (items: any[]) => items.forEach(item => {
    if (item.path) existingPaths.add(item.path);
    if (item.children?.length) collectPaths(item.children);
  });
  collectPaths(merged);
  const requiredEntries = deepClone(systemMenu).filter((node: any) =>
    typeof node.path === "string" && node.path.startsWith("/tgdrive/") && !existingPaths.has(node.path)
  );
  return [...merged, ...requiredEntries];
};

const normalizeMenuData = (nodes: any[]): any[] =>
  nodes.map(node => ({
    ...node,
    meta:
      node.path === "/tgdrive/telegram/accounts" && node.meta?.title === "Telegram 账号"
        ? { ...node.meta, title: "账号管理" }
        : node.path === "/tgdrive/telegram/dialogs" && node.meta?.title === "Telegram 对话"
          ? { ...node.meta, title: "群组/频道管理" }
          : node.meta,
    children: node.children?.length ? normalizeMenuData(node.children) : node.children
  }));

export const getRoutersAPI = () => {
  const stored = localStorage.getItem("snowadmin-menu-data");
  const menuData = stored
    ? mergeRequiredNavigationEntries(removeDeletedNavigationEntries(normalizeMenuData(treeSort(JSON.parse(stored)))))
    : treeSort(buildTreeOptimized([...deepClone(systemMenu)]));
  const userInfo = JSON.parse(localStorage.getItem("user-info") || "{}");
  const userRoles = userInfo?.account?.roles?.length
    ? userInfo.account.roles
    : userInfo?.account?.user?.role
      ? [userInfo.account.user.role]
      : userInfo?.token === "Admin-Token"
        ? ["admin"]
        : ["common"];

  const filterTree = (nodes: any[]): any[] =>
    filterByDisable(
      nodes
        .filter(node => node?.meta?.type !== 3)
        .map(node => ({
          ...node,
          children: node.children?.length ? filterTree(node.children) : null
        })),
      userRoles
    );

  return Promise.resolve({ data: treeSort(filterTree(deepClone(menuData))) });
};

// 获取字典数据
export const getDictAPI = () => {
  return axios({
    url: "/mock/system/getDict",
    method: "get"
  });
};

// 获取部门数据
export const getDivisionAPI = () => {
  return axios({
    url: "/mock/system/getDivision",
    method: "get"
  });
};

// 获取角色数据
export const getRoleAPI = () => {
  return axios({
    url: "/mock/system/getRole",
    method: "get"
  });
};

// 获取账户数据
export const getAccountAPI = () => {
  return axios({
    url: "/mock/system/getAccount",
    method: "get"
  });
};

// 获取菜单管理列表
export const getMenuListAPI = () => {
  const stored = localStorage.getItem("snowadmin-menu-data");
  const data = stored
    ? mergeRequiredNavigationEntries(removeDeletedNavigationEntries(normalizeMenuData(treeSort(JSON.parse(stored)))))
    : treeSort(buildTreeOptimized([...deepClone(systemMenu), ...deepClone(permissionData)]));
  return Promise.resolve({ data });
};

// 根据角色获取权限数据
export const getUserPermissionAPI = (params: { role: string }) => {
  return axios({
    url: "/mock/menu/getUserPermission",
    method: "get",
    params
  });
};
