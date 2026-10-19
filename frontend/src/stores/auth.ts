import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi } from "@/api";

export interface UserInfo {
  id: number;
  username: string;
  nickname: string;
  role: "super_admin" | "lawyer" | "user";
  avatar: string;
  status: string;
  created_at: string;
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string>(localStorage.getItem("alawyer-token") || "");
  const user = ref<UserInfo | null>(
    JSON.parse(localStorage.getItem("alawyer-user") || "null")
  );

  const isLoggedIn = computed(() => !!token.value && !!user.value);
  const roleLabel = computed(() => {
    if (!user.value) return "";
    return { super_admin: "超级管理员", lawyer: "律师", user: "普通用户" }[user.value.role] || "";
  });

  function setSession(t: string, u: UserInfo) {
    token.value = t;
    user.value = u;
    localStorage.setItem("alawyer-token", t);
    localStorage.setItem("alawyer-user", JSON.stringify(u));
  }

  function updateUser(u: Partial<UserInfo>) {
    if (user.value) {
      user.value = { ...user.value, ...u };
      localStorage.setItem("alawyer-user", JSON.stringify(user.value));
    }
  }

  async function refreshMe() {
    if (!token.value) return;
    try {
      const u = await authApi.me();
      updateUser(u);
    } catch {
      logout();
    }
  }

  function logout() {
    token.value = "";
    user.value = null;
    localStorage.removeItem("alawyer-token");
    localStorage.removeItem("alawyer-user");
  }

  return { token, user, isLoggedIn, roleLabel, setSession, updateUser, refreshMe, logout };
});