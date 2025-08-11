import { useCallback } from "react";

const STORAGE_KEY = "bj_case_profiles_v1";

export default function useCaseStorage() {
  const loadCases = useCallback(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch (err) {
      console.error("Failed to load cases", err);
      return [];
    }
  }, []);

  const saveCase = useCallback(
    (rec) => {
      try {
        const all = loadCases();
        all.unshift(rec);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
      } catch (err) {
        console.error("Failed to save case", err);
      }
    },
    [loadCases]
  );

  return { loadCases, saveCase };
}
