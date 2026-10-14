import { deepClone, buildTreeOptimized, filterByDisable, treeSort } from "@/utils/tree";
import { systemMenu, permissionData } from "@/config/system-menu";
import axios from "@/api";

// 获取菜单数据
// 菜单管理与动态路由共用同一份持久化配置，避免“管理页改了，但侧边栏仍使用旧 mock 数据”。
// 从历史本地菜单配置中清理已移除的模板导航，避免旧缓存重新生成这些路由。
const DELETED_NAVIGATION_PATHS = [
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

// 递归复制菜单树时只处理子节点，不执行补齐逻辑，避免每个子树都重复插入“组件管理”目录。
const cloneMenuTree = (nodes: any[]): any[] =>
  nodes.map(node => ({
    ...node,
    children: node.children?.length ? cloneMenuTree(node.children) : node.children
  }));

// 防止历史菜单数据中同级路由重复，合并重复项的子节点而不丢失已有菜单。
const deduplicateMenuEntries = (nodes: any[]): any[] => {
  const unique: any[] = [];
  const byPath = new Map<string, any>();
  for (const node of nodes) {
    const copy = { ...node, children: node.children?.length ? deduplicateMenuEntries(node.children) : node.children };
    const existing = copy.path ? byPath.get(copy.path) : undefined;
    if (!existing) {
      unique.push(copy);
      if (copy.path) byPath.set(copy.path, copy);
      continue;
    }
    if (copy.children?.length) {
      existing.children = deduplicateMenuEntries([...(existing.children || []), ...copy.children]);
    }
  }
  return unique;
};

// 历史 localStorage 菜单可能早于 TGDrive 页面，补齐默认 TGDrive 路由，避免登录后 HOME_PATH 指向不存在的动态路由。
const mergeRequiredNavigationEntries = (nodes: any[]): any[] => {
  const merged = cloneMenuTree(nodes);
  const existingPaths = new Set<string>();
  const collectPaths = (items: any[]) => items.forEach(item => {
    if (item.path) existingPaths.add(item.path);
    if (item.children?.length) collectPaths(item.children);
  });
  collectPaths(merged);
  const menuEntries = deepClone(systemMenu);
  const requiredEntries = menuEntries.filter((node: any) =>
    typeof node.path === "string" && node.path.startsWith("/tgdrive/") && !existingPaths.has(node.path)
  );

  // 历史 localStorage 菜单可能仍是旧版本；恢复系统组件目录时，也要把它及两个子菜单补回持久化菜单树。
  const componentRoot = menuEntries.find((node: any) => node.path === "/component");
  if (componentRoot) {
    const componentChildren = menuEntries.filter((node: any) => node.parentId === componentRoot.id);
    const existingComponentRoot = merged.find((node: any) => node.path === componentRoot.path);
    if (!existingComponentRoot) {
      merged.push({ ...componentRoot, children: componentChildren });
    } else {
      const children = existingComponentRoot.children?.length ? existingComponentRoot.children : [];
      const childPaths = new Set(children.map((node: any) => node.path));
      children.push(...componentChildren.filter((node: any) => !childPaths.has(node.path)));
      existingComponentRoot.children = children;
    }
  }

  return deduplicateMenuEntries([...merged, ...requiredEntries]);
};

const normalizeMenuData = (nodes: any[]): any[] =>
  nodes.map(node => {
    const isBasicSettings = node.path === "/system/userinfo" || node.path === "/system/basic-settings";
    return {
      ...node,
      ...(isBasicSettings
        ? {
            path: "/system/basic-settings",
            name: "basic-settings",
            component: "system/basic-settings/basic-settings"
          }
        : {}),
      meta: isBasicSettings
        ? { ...node.meta, title: "basic-settings" }
        : node.path === "/tgdrive/telegram/accounts" && node.meta?.title === "Telegram 账号"
          ? { ...node.meta, title: "账号管理" }
          : node.path === "/tgdrive/telegram/dialogs" && node.meta?.title === "Telegram 对话"
            ? { ...node.meta, title: "群组/频道管理" }
            : node.meta,
      children: node.children?.length ? normalizeMenuData(node.children) : node.children
    };
  });

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
        .filter(node => node?.meta?.type !== 3 && node?.meta?.disable !== true)
        .map(node => ({
          ...node,
          children: node.children?.length ? filterTree(node.children) : null
        })),
      userRoles
    );

  const fallback = () => ({ data: treeSort(filterTree(deepClone(menuData))) });
  return axios({ url: "/auth/permissions", method: "get" })
    .then((permissions: any) => {
      if (!Array.isArray(permissions)) return fallback();
      const allowed = new Set(permissions.map((id: any) => String(id)));
      const applyPermissions = (nodes: any[]): any[] => nodes
        .filter(node => node?.meta?.type !== 3)
        .map(node => ({
          ...node,
          children: node.children?.length ? applyPermissions(node.children) : null
        }))
        .filter(node => allowed.has(String(node.id)) || Boolean(node.children?.length));
      return { data: treeSort(applyPermissions(deepClone(menuData))) };
    })
    .catch(() => fallback());
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
export const getRoleAPI = () => axios({ url: "/admin/roles", method: "get" });

export const createRoleAPI = (data: any) => axios({ url: "/admin/roles", method: "post", data });

export const updateRoleAPI = (id: number, data: any) => axios({ url: `/admin/roles/${id}`, method: "put", data });

export const deleteRoleAPI = (id: number) => axios({ url: `/admin/roles/${id}`, method: "delete" });

export const updateRolePermissionsAPI = (id: number, permissions: string[]) =>
  axios({ url: `/admin/roles/${id}/permissions`, method: "put", data: { permissions } });

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
export const getUserPermissionAPI = (params: { role: string }) =>
  axios({ url: `/admin/roles/by-code/${encodeURIComponent(params.role)}/permissions`, method: "get" });
