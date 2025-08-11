import React, { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { loadCases } from "../CaseProfileApp";

export default function CaseLandingPage({ onNew, onOpen }) {
  const [cases, setCases] = useState([]);
  useEffect(() => { setCases(loadCases()); }, []);
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">My Cases</h1>
        <Button className="rounded-2xl" onClick={onNew}>+ New Case</Button>
      </div>
      {cases.length === 0 ? (
        <p className="text-slate-600">No cases yet. Click "New Case" to start.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cases.map((c) => (
            <Card key={c.id} onClick={() => onOpen(c)} className="rounded-2xl border shadow-sm bg-white cursor-pointer hover:shadow-md transition">
              <CardContent className="p-4">
                <h2 className="text-lg font-medium mb-1">{c.caseName}</h2>
                <p className="text-xs text-slate-500 mb-2">{c.jurisdiction || "No jurisdiction"}</p>
                <p className="text-sm line-clamp-3">{c.description || "No description"}</p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {(c.tags || []).map((t) => (
                    <span key={t} className="text-xs bg-slate-100 rounded-full px-2 py-0.5">{t}</span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
