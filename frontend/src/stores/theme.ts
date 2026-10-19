import { defineStore } from "pinia";
import { ref, watch } from "vue";

export const useThemeStore = defineStore("theme", () => {
  const mode = ref<"light" | "dark">("light");

  function apply() {
    document.documentElement.classList.toggle("dark", mode.value === "dark");
  }

  function init() {
    const saved = localStorage.getItem("alawyer-theme");
    mode.value = saved === "dark" ? "dark" : "light";
    apply();
    watch(mode, (v) => {
      localStorage.setItem("alawyer-theme", v);
      apply();
    });
  }

  function toggle() {
    mode.value = mode.value === "dark" ? "light" : "dark";
  }

  return { mode, init, toggle };
});