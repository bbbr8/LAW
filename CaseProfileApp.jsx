import React, { useState } from "react";
import CaseLandingPage from "./components/CaseLandingPage";
import CaseDetail from "./components/CaseDetail";
import CaseProfileCreator from "./components/CaseProfileCreator";

export const STORAGE_KEY = "bj_case_profiles_v1";
export const loadCases = () => {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); } catch { return []; }
};
export const saveCase = (rec) => {
  const all = loadCases();
  all.unshift(rec);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
};

export default function CaseProfileApp() {
  const [view, setView] = useState("landing");
  const [selectedCase, setSelectedCase] = useState(null);
  return view === "landing" ? (
    <CaseLandingPage onNew={() => setView("creator")} onOpen={(c) => { setSelectedCase(c); setView("detail"); }} />
  ) : view === "detail" ? (
    <CaseDetail caseData={selectedCase} onBack={() => setView("landing")} />
  ) : (
    <CaseProfileCreator onSaved={() => setView("landing")} onCancel={() => setView("landing")} />
  );
}
