import axios from "axios";

const http = axios.create({ withCredentials: true });

export const getAccountsAPI = () => http.get("/api/telegram/accounts");
export const getAccountInfoAPI = (id: number) => http.get(`/api/telegram/accounts/${id}/info`);
// Account enable/disable is intentionally disabled for now.
 // export const setAccountEnabledAPI = (id: number, enabled: boolean) =>
 //   http.put(`/api/telegram/accounts/${id}/enabled`, { enabled });
export const deleteAccountAPI = (id: number) => http.delete(`/api/telegram/accounts/${id}`);
export const getDeletedAccountsAPI = () => http.get("/api/telegram/accounts/deleted");
export const restoreDeletedAccountAPI = (session: string) =>
  http.post("/api/telegram/accounts/restore", { session });
export const updateAccountProfileAPI = (
  id: number,
  data: { login_name?: string; nickname?: string; username?: string }
) => http.put(`/api/telegram/accounts/${id}/profile`, data);
export const startAccountPhoneChangeAPI = (id: number, phone: string) =>
  http.post(`/api/telegram/accounts/${id}/phone/start`, { phone });
export const confirmAccountPhoneChangeAPI = (id: number, code: string) =>
  http.post(`/api/telegram/accounts/${id}/phone/confirm`, { code });
export const startAccountEmailChangeAPI = (id: number, email: string) =>
  http.post(`/api/telegram/accounts/${id}/email/start`, { email });
export const confirmAccountEmailChangeAPI = (id: number, code: string) =>
  http.post(`/api/telegram/accounts/${id}/email/confirm`, { code });

export const startAccountLoginAPI = (data: { login_name: string; phone: string }) =>
  http.post("/api/telegram/accounts/login/start", data);
export const getAccountLoginStatusAPI = (loginId: string) =>
  http.get(`/api/telegram/accounts/login/${loginId}`);
export const submitAccountLoginCodeAPI = (data: { login_id: string; code: string }) =>
  http.post("/api/telegram/accounts/login/code", data);
export const submitAccountLoginPasswordAPI = (data: { login_id: string; password: string }) =>
  http.post("/api/telegram/accounts/login/password", data);
export const cancelAccountLoginAPI = (loginId: string) =>
  http.post("/api/telegram/accounts/login/cancel", { login_id: loginId });

export const getDialogsAPI = () => http.get("/api/telegram/dialogs");
export const refreshDialogsAPI = () => http.post("/api/telegram/dialogs/refresh");
export const deleteDialogAPI = (accountId: number, chatId: number) =>
  http.delete(`/api/telegram/accounts/${accountId}/dialogs/${chatId}`);
export const setDialogEnabledAPI = (accountId: number, chatId: number, enabled: boolean) =>
  http.put(`/api/telegram/accounts/${accountId}/dialogs/${chatId}/enabled`, { enabled });

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
