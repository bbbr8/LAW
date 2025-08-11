import React from "react";
import { Button } from "@/components/ui/button";

export default function CaseDetail({ caseData, onBack }) {
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <Button variant="outline" onClick={onBack} className="mb-6">← Back</Button>
      <h1 className="text-3xl font-bold mb-4">{caseData.caseName}</h1>
      <p className="mb-2"><strong>Case Number:</strong> {caseData.caseNumber || "—"}</p>
      <p className="mb-2"><strong>Jurisdiction:</strong> {caseData.jurisdiction || "—"}</p>
      <p className="mb-2"><strong>Filing Date:</strong> {caseData.filingDate || "—"}</p>
      <p className="mb-4"><strong>Description:</strong> {caseData.description || "—"}</p>
      <h2 className="text-xl font-semibold mt-6 mb-2">Parties</h2>
      {caseData.parties?.length ? (
        <ul className="list-disc ml-6">
          {caseData.parties.map((p) => (
            <li key={p.id || p.name}>{p.name} – {p.role}</li>
          ))}
        </ul>
      ) : (
        <p>No parties listed.</p>
      )}
    </div>
  );
}
