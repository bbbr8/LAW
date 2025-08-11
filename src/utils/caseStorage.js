const STORAGE_KEY = "bj_case_profiles_v1";

export const loadCases = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
};

export const saveCase = (rec) => {
  const all = loadCases();
  all.unshift(rec);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
};

