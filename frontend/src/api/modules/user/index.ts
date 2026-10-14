import axios from "axios";

export const loginAPI = async (data: { username: string; password: string; totp_code?: string }) => {
  const response = await axios.post("/auth/login", data, { withCredentials: true });
  return {
    data: {
      token: response.data.role === "admin" ? "Admin-Token" : "Common-Token",
      user: response.data
    }
  };
};

export const getUserInfoAPI = async (_params?: Record<string, unknown>) => {
  const response = await axios.get("/auth/me", { withCredentials: true });
  const user = response.data;
  return {
    data: {
      user,
      roles: user.role ? [user.role] : [],
      permissions: []
    }
  };
};

export const updateUserProfileAPI = async (data: { username: string; current_password: string; new_password?: string | null }) => {
  const response = await axios.put("/auth/profile", data, { withCredentials: true });
  return { data: response.data };
};

export const updateUserAvatarAPI = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await axios.post("/auth/avatar", formData, { withCredentials: true });
  return { data: response.data };
};

export const getTotpStatusAPI = async () => {
  const response = await axios.get("/auth/totp", { withCredentials: true });
  return { data: response.data as { enabled: boolean } };
};

export const setupTotpAPI = async (current_password: string) => {
  const response = await axios.post("/auth/totp/setup", { current_password }, { withCredentials: true });
  return { data: response.data as { secret: string; otpauth_url: string } };
};

export const enableTotpAPI = async (code: string) => {
  const response = await axios.post("/auth/totp/enable", { code }, { withCredentials: true });
  return { data: response.data as { enabled: boolean } };
};

export const disableTotpAPI = async (current_password: string, code?: string) => {
  const response = await axios.post("/auth/totp/disable", { current_password, code }, { withCredentials: true });
  return { data: response.data as { enabled: boolean } };
};
