import axios from "axios";

const http = axios.create({ withCredentials: true });

export const getAccountsAPI = () => http.get("/api/telegram/accounts");
export const getAccountInfoAPI = (id: number) => http.get(`/api/telegram/accounts/${id}/info`);
export const setAccountEnabledAPI = (id: number, enabled: boolean) =>
  http.put(`/api/telegram/accounts/${id}/enabled`, { enabled });
export const getDialogsAPI = (accountId: number) => http.get(`/api/telegram/accounts/${accountId}/dialogs`);
export const deleteDialogAPI = (accountId: number, chatId: number) =>
  http.delete(`/api/telegram/accounts/${accountId}/dialogs/${chatId}`);

export const getSourcesAPI = () => http.get("/api/telegram/sources");
export const createSourceAPI = (data: { account_id: number; telegram_chat_id: number; name: string }) =>
  http.post("/api/telegram/sources", data);
export const setSourceEnabledAPI = (id: number, enabled: boolean) =>
  http.put(`/api/telegram/sources/${id}/enabled`, { enabled });
export const deleteSourceAPI = (id: number) => http.delete(`/api/telegram/sources/${id}`);
export const reconnectTelegramAPI = () => http.post("/api/telegram/reconnect");
export const reconcileTelegramAPI = () => http.post("/api/telegram/reconcile");

export const getCategoriesAPI = () => http.get("/api/admin/categories");
export const createCategoryAPI = (name: string) => http.post("/api/admin/categories", { name });
export const updateCategoryAPI = (id: number, name: string) => http.put(`/api/admin/categories/${id}`, { name });
export const deleteCategoryAPI = (id: number) => http.delete(`/api/admin/categories/${id}`);
export const setResourceCategoriesAPI = (id: number, category_ids: number[]) =>
  http.put(`/api/admin/resources/${id}/categories`, { category_ids });
export const deleteShareAPI = (id: number) => http.delete(`/api/admin/shares/${id}`);

export const getResourceAPI = (id: number) => http.get(`/catalog/${id}`);
export const getResourcesAPI = (params: { page?: number; size?: number; category_id?: number; sort?: string; order?: string }) =>
  http.get("/catalog", { params });
export const searchResourcesAPI = (params: { q: string; category_id?: number; limit?: number }) =>
  http.get("/catalog/search", { params });
export const createShareAPI = (id: number) => http.post(`/resources/${id}/share`);

export const getActiveDownloadsAPI = () => http.get("/api/admin/downloads/active");
export const getDownloadHistoryAPI = () => http.get("/api/admin/downloads/history");
export const deleteDownloadAPI = (id: number) => http.delete(`/api/admin/downloads/${id}`);
