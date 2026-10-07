import { deepClone, buildTreeOptimized, treeSort } from "@/mock/_utils";
import { systemMenu, permissionData } from "@/mock/_data/system_menu";
import axios from "@/api";

// 获取菜单数据
export const getRoutersAPI = () => {
  return axios({
    url: "/mock/menu/getRouters",
    method: "get"
  });
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
    ? JSON.parse(stored)
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
