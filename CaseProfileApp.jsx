import React, { useState } from "react";
import CaseLandingPage from "./CaseLandingPage";
import CaseDetail from "./CaseDetail";
import CaseProfileCreator from "./CaseProfileCreator";

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

