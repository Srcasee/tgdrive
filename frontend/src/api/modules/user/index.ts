import axios from "axios";

export const loginAPI = async (data: { username: string; password: string }) => {
  const response = await axios.post("/auth/login", data, { withCredentials: true });
  return {
    data: {
      token: "cookie",
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
