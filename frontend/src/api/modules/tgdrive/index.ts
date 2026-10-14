import axios from "axios";

const http = axios.create({ withCredentials: true });

export const getAccountsAPI = () => http.get("/api/telegram/accounts");
export const getAccountInfoAPI = (id: number) => http.get(`/api/telegram/accounts/${id}/info`);
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
export const createSourceAPI = (accountId: number, chatId: number) =>
  http.post(`/api/telegram/sources/accounts/${accountId}/chats/${chatId}`);
export const setDialogSourceEnabledAPI = (accountId: number, chatId: number, enabled: boolean) =>
  http.put(`/api/telegram/sources/accounts/${accountId}/chats/${chatId}/enabled`, { enabled });
export const deleteSourceAPI = (id: number) => http.delete(`/api/telegram/sources/${id}`);

export const getCategoriesAPI = () => http.get("/api/admin/categories");
export const deleteShareAPI = (id: number) => http.delete(`/api/admin/shares/${id}`);

export const getResourceTreeAPI = () => http.get("/catalog/tree");
export const getResourceAPI = (id: number) => http.get(`/catalog/${id}`);
export const getResourcesAPI = (params: { page?: number; size?: number; account_id?: number; chat_id?: number; topic_id?: number; sort?: string; order?: string }) =>
  http.get("/catalog", { params });
export const searchResourcesAPI = (params: { q: string; account_id?: number; chat_id?: number; topic_id?: number; limit?: number }) =>
  http.get("/catalog/search", { params });
export const createShareAPI = (id: number, expires_at: string | null = null) =>
  http.post(`/resources/${id}/share`, { expires_at });
export const createTopicShareAPI = (data: { account_id: number; chat_id: number; topic_id: number }) =>
  http.post("/topics/share", data);
export const deleteTopicShareAPI = (id: number) => http.delete(`/api/admin/topic-shares/${id}`);

export type DownloadStatus = "active" | "completed" | "failed";
export const getDownloadRecordsAPI = (params: { status: DownloadStatus; page?: number; size?: number }) =>
  http.get("/api/admin/downloads", { params });
export const bulkDeleteDownloadsAPI = (ids: number[]) =>
  http.post("/api/admin/downloads/bulk-delete", { ids });
