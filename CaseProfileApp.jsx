import React, { useState, useEffect, useMemo, useRef } from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Textarea } from "./components/ui/textarea";
import { Label } from "./components/ui/label";
import { Switch } from "./components/ui/switch";
import { Separator } from "./components/ui/separator";
import { Plus, FileText, Upload, Trash2, Info, ChevronLeft, ChevronRight, CheckCircle2, Tags } from "lucide-react";

const STORAGE_KEY = "bj_case_profiles_v1";
const loadCases = () => {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); } catch { return []; }
};
const saveCase = (rec) => {
  const all = loadCases();
  all.unshift(rec);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
};

function CaseLandingPage({ onNew, onOpen }) {
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

function CaseDetail({ caseData, onBack }) {
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

function CaseProfileCreator({ onSaved, onCancel }) {
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);
  const [draft, setDraft] = useState({
    caseName: "",
    caseNumber: "",
    userRole: "Plaintiff",
    jurisdiction: "",
    filingDate: "",
    description: "",
    parties: [],
    tags: [],
    files: [],
    ocrEnabled: true,
    extractForensicMeta: true,
    summarizeOnUpload: true,
  });
  const canContinue = useMemo(() => {
    if (step === 1) return draft.caseName.trim().length > 0;
    return true;
  }, [step, draft.caseName]);
  const update = (key, value) => setDraft((d) => ({ ...d, [key]: value }));
  const onPickFiles = () => inputRef.current?.click();
  const onFilesSelected = (files) => { if (!files) return; update("files", [...draft.files, ...Array.from(files)]); };
  const onDrop = (e) => { e.preventDefault(); if (e.dataTransfer.files?.length) onFilesSelected(e.dataTransfer.files); };
  const removeFile = (idx) => update("files", draft.files.filter((_, i) => i !== idx));
  const analyzeUploads = async () => {
    setBusy(true);
    await new Promise((r) => setTimeout(r, 800));
    const detected = [
      { id: crypto.randomUUID(), name: "Michael Bryce Jones", role: "Plaintiff" },
      { id: crypto.randomUUID(), name: "Suited Homes / Jeff Strong", role: "Contractor" },
      { id: crypto.randomUUID(), name: "Fortis Private Bank", role: "Bank" },
      { id: crypto.randomUUID(), name: "Colby Peterson", role: "Contractor" },
    ];
    const autoTags = ["construction", "bank-draws", "fraud-investigation", "Utah", "2018-2019"];
    setDraft((d) => ({
      ...d,
      parties: d.parties.length ? d.parties : detected,
      tags: d.tags.length ? d.tags : autoTags,
      description: d.description || "Auto-summary: Residential construction dispute with disputed draws and alleged forged signatures. Core parties: homeowner, builder, lender.",
    }));
    setBusy(false);
  };
  const addParty = () => setDraft((d) => ({ ...d, parties: [...d.parties, { id: crypto.randomUUID(), name: "", role: "Other" }] }));
  const setPartyField = (idx, key, value) => setDraft((d) => ({ ...d, parties: d.parties.map((p, i) => (i === idx ? { ...p, [key]: value } : p)) }));
  const removeParty = (idx) => setDraft((d) => ({ ...d, parties: d.parties.filter((_, i) => i !== idx) }));
  const [newTag, setNewTag] = useState("");
  const addTag = (t) => { const trimmed = t.trim(); if (!trimmed || draft.tags.includes(trimmed)) return; update("tags", [...draft.tags, trimmed]); };
  const onCreateProfile = async () => {
    setBusy(true);
    try {
      const fileDescs = draft.files.map((f) => ({ name: f.name, size: f.size, type: f.type }));
      const record = { id: crypto.randomUUID(), createdAt: new Date().toISOString(), ...draft, files: fileDescs };
      saveCase(record);
      onSaved();
    } finally { setBusy(false); }
  };
  const StepPill = ({ n, label, active, done }) => (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-2xl border ${active ? "border-black/20 bg-black/5" : "border-black/10 bg-white"}`}>
      <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-medium ${done ? "bg-green-100" : active ? "bg-black text-white" : "bg-black/10"}`}>
        {done ? <CheckCircle2 className="h-4 w-4" /> : n}
      </div>
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
  const Chip = ({ text, onRemove }) => (
    <span className="inline-flex items-center gap-2 rounded-2xl border border-black/10 px-3 py-1 text-sm bg-white shadow-sm">
      <Tags className="h-3.5 w-3.5" /> {text}
      {onRemove && (
        <button onClick={onRemove} className="hover:text-red-600" aria-label={`remove ${text}`}>
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </span>
  );
  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-white to-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Create a Case</h1>
            <p className="text-sm text-slate-600 mt-1">Upload a document; we’ll OCR, extract parties, and draft a summary.</p>
          </div>
          <div className="flex gap-2 items-center">
            <Button variant="outline" className="rounded-2xl" onClick={onCancel}>Back to cases</Button>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <StepPill n={1} label="Basics" active={step===1} done={step>1} />
          <StepPill n={2} label="Parties & Roles" active={step===2} done={step>2} />
          <StepPill n={3} label="Documents" active={step===3} done={step>3} />
          <StepPill n={4} label="Review & Create" active={step===4} />
        </div>
        <Card className="mt-6 rounded-2xl shadow-sm border-slate-200">
          <CardContent className="p-6">
            {step === 1 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div><Label htmlFor="caseName">Case name</Label><Input id="caseName" placeholder="e.g., Jones v. Suited Homes" value={draft.caseName} onChange={(e)=>update("caseName", e.target.value)} className="mt-2" /></div>
                <div><Label htmlFor="caseNo">Case number (optional)</Label><Input id="caseNo" placeholder="e.g., 180401234" value={draft.caseNumber} onChange={(e)=>update("caseNumber", e.target.value)} className="mt-2" /></div>
                <div><Label htmlFor="juris">Court / Jurisdiction</Label><Input id="juris" placeholder="e.g., 4th District Court, Utah County, UT" value={draft.jurisdiction} onChange={(e)=>update("jurisdiction", e.target.value)} className="mt-2" /></div>
                <div><Label htmlFor="date">Filing date</Label><Input id="date" type="date" value={draft.filingDate} onChange={(e)=>update("filingDate", e.target.value)} className="mt-2" /></div>
                <div className="md:col-span-2"><Label>Case description (optional)</Label><Textarea rows={4} placeholder="Short context for this profile…" value={draft.description} onChange={(e)=>update("description", e.target.value)} className="mt-2" /></div>
              </motion.div>
            )}
            {step === 2 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                <div className="flex items-center justify-between"><div><h3 className="text-lg font-medium">Parties</h3><p className="text-sm text-slate-600">Add people and organizations involved.</p></div><Button className="rounded-2xl" onClick={addParty}><Plus className="h-4 w-4 mr-2"/>Add party</Button></div>
                <div className="space-y-4">
                  {draft.parties.length === 0 && (<div className="rounded-xl border border-dashed p-6 text-sm text-slate-600">No parties yet. Click <strong>Add party</strong> or analyze uploads in the next step.</div>)}
                  {draft.parties.map((p, idx) => (
                    <div key={p.id} className="grid grid-cols-1 md:grid-cols-12 gap-3 rounded-2xl border p-4 bg-white">
                      <div className="md:col-span-5"><Label>Name</Label><Input value={p.name} onChange={(e)=>setPartyField(idx, "name", e.target.value)} placeholder="e.g., Fortis Private Bank" className="mt-2" /></div>
                      <div className="md:col-span-3"><Label>Role</Label><select className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={p.role} onChange={(e)=>setPartyField(idx, "role", e.target.value)}>{["Plaintiff","Defendant","Witness","Attorney","Bank","Contractor","Other"].map((r) => (<option key={r} value={r}>{r}</option>))}</select></div>
                      <div className="md:col-span-3"><Label>Notes (optional)</Label><Input value={p.notes || ""} onChange={(e)=>setPartyField(idx, "notes", e.target.value)} placeholder="e.g., lender contact name" className="mt-2" /></div>
                      <div className="md:col-span-1 flex items-end justify-end"><Button variant="outline" className="rounded-xl" onClick={()=>removeParty(idx)}><Trash2 className="h-4 w-4"/></Button></div>
                    </div>
                  ))}
                </div>
                <div><Label>Tags</Label><div className="mt-2 flex flex-wrap gap-2">{draft.tags.map((t, i) => (<Chip key={t} text={t} onRemove={() => update("tags", draft.tags.filter((_, idx) => idx !== i))} />))}</div><div className="mt-3 flex gap-2"><Input value={newTag} onChange={(e)=>setNewTag(e.target.value)} placeholder="Add a tag…" className="max-w-xs"/><Button type="button" className="rounded-2xl" onClick={()=>{ addTag(newTag); setNewTag(""); }}>Add</Button></div></div>
              </motion.div>
            )}
            {step === 3 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="md:col-span-2">
                    <Label>Upload documents</Label>
                    <div onDragOver={(e)=>e.preventDefault()} onDrop={onDrop} className="mt-2 rounded-2xl border-2 border-dashed border-slate-300 bg-white p-8 text-center cursor-pointer" onClick={onPickFiles}>
                      <Upload className="mx-auto h-8 w-8"/>
                      <p className="mt-2 text-sm text-slate-600">Drag & drop files here, or click to browse</p>
                      <p className="text-xs text-slate-500">PDF, DOCX, PNG, JPG</p>
                      <input ref={inputRef} type="file" className="hidden" multiple onChange={(e)=>onFilesSelected(e.target.files)} />
                    </div>
                    {draft.files.length > 0 && (
                      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                        {draft.files.map((f, i) => (
                          <div key={`${f.name}-${i}`} className="flex items-center justify-between rounded-xl border bg-white p-3">
                            <div className="flex items-center gap-3"><FileText className="h-5 w-5"/><div><div className="text-sm font-medium truncate max-w-[220px]" title={f.name}>{f.name}</div><div className="text-xs text-slate-500">{(f.size/1024/1024).toFixed(2)} MB</div></div></div>
                            <button className="text-slate-600 hover:text-red-600" onClick={()=>removeFile(i)}><Trash2 className="h-4 w-4"/></button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="md:col-span-1">
                    <Label>Automation</Label>
                    <div className="mt-2 space-y-4 rounded-2xl border p-4 bg-white">
                      <div className="flex items-center justify-between"><div className="text-sm"><div className="font-medium">OCR & entity extraction</div><div className="text-slate-500">Detect parties, attorneys, dates</div></div><Switch checked={draft.ocrEnabled} onCheckedChange={(v)=>update("ocrEnabled", !!v)} /></div>
                      <div className="flex items-center justify-between"><div className="text-sm"><div className="font-medium">Forensic metadata</div><div className="text-slate-500">Hashes, sizes, timestamps</div></div><Switch checked={draft.extractForensicMeta} onCheckedChange={(v)=>update("extractForensicMeta", !!v)} /></div>
                      <div className="flex items-center justify-between"><div className="text-sm"><div className="font-medium">Auto-summary</div><div className="text-slate-500">Generate an overview</div></div><Switch checked={draft.summarizeOnUpload} onCheckedChange={(v)=>update("summarizeOnUpload", !!v)} /></div>
                      <Separator className="my-2"/>
                      <Button className="w-full rounded-2xl" disabled={busy || draft.files.length===0} onClick={analyzeUploads}>{busy ? "Analyzing…" : "Analyze uploads"}</Button>
                    </div>
                  </div>
                </div>
                {(draft.parties.length > 0 || draft.description) && (
                  <div className="rounded-2xl border p-4 bg-white">
                    <div className="flex items-center gap-2 mb-2"><Info className="h-4 w-4"/><h4 className="font-medium">Auto-detected preview</h4></div>
                    {draft.parties.length>0 && (
                      <div className="mb-3"><div className="text-xs text-slate-500 mb-2">Parties</div><div className="flex flex-wrap gap-2">{draft.parties.map((p) => (<span key={p.id} className="inline-flex items-center gap-2 rounded-xl border px-3 py-1 text-sm bg-slate-50"><span className="font-medium">{p.name || "(unnamed)"}</span><span className="text-xs text-slate-600">{p.role}</span></span>))}</div></div>
                    )}
                    {draft.description && (<div><div className="text-xs text-slate-500 mb-2">Summary</div><p className="text-sm leading-relaxed">{draft.description}</p></div>)}
                  </div>
                )}
              </motion.div>
            )}
            {step === 4 && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-4">
                    <div className="rounded-2xl border p-4 bg-white">
                      <h4 className="font-medium">Basics</h4>
                      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                        <div><span className="text-slate-500">Case</span><div className="font-medium">{draft.caseName || "—"}</div></div>
                        <div><span className="text-slate-500">Number</span><div className="font-medium">{draft.caseNumber || "—"}</div></div>
                        <div><span className="text-slate-500">Jurisdiction</span><div className="font-medium">{draft.jurisdiction || "—"}</div></div>
                        <div><span className="text-slate-500">Filing date</span><div className="font-medium">{draft.filingDate || "—"}</div></div>
                        <div><span className="text-slate-500">Your role</span><div className="font-medium">{draft.userRole}</div></div>
                      </div>
                      {draft.description && (<div className="mt-4"><div className="text-slate-500 text-sm">Summary</div><p className="text-sm mt-1 leading-relaxed">{draft.description}</p></div>)}
                    </div>
                    <div className="rounded-2xl border p-4 bg-white">
                      <h4 className="font-medium">Parties</h4>
                      {draft.parties.length === 0 ? (<p className="text-sm text-slate-600 mt-2">None added.</p>) : (
                        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">{draft.parties.map((p) => (<div key={p.id} className="rounded-xl border p-3"><div className="font-medium">{p.name || "(unnamed)"}</div><div className="text-xs text-slate-600">{p.role}</div>{p.notes && <div className="text-xs mt-1 text-slate-600">{p.notes}</div>}</div>))}</div>
                      )}
                    </div>
                    <div className="rounded-2xl border p-4 bg-white">
                      <h4 className="font-medium">Files</h4>
                      {draft.files.length === 0 ? (<p className="text-sm text-slate-600 mt-2">No documents uploaded.</p>) : (
                        <ul className="mt-3 space-y-2 text-sm">{draft.files.map((f, i) => (<li key={`${f.name}-${i}`} className="flex items-center justify-between border rounded-xl p-2"><div className="flex items-center gap-3"><FileText className="h-4 w-4"/> {f.name}</div><span className="text-xs text-slate-500">{(f.size/1024/1024).toFixed(2)} MB</span></li>))}</ul>
                      )}
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div className="rounded-2xl border p-4 bg-white">
                      <h4 className="font-medium">Ready?</h4>
                      <p className="text-sm text-slate-600">Saves locally for now. Wire to your backend later.</p>
                      <Button className="w-full mt-3 rounded-2xl" onClick={onCreateProfile} disabled={busy}>{busy ? "Creating…" : "Create profile"}</Button>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
            <div className="mt-8 flex items-center justify-between">
              <Button variant="outline" className="rounded-2xl" onClick={()=>setStep((s)=>Math.max(1, s-1))} disabled={step===1}><ChevronLeft className="mr-2 h-4 w-4"/>Back</Button>
              {step < 4 && (<Button className="rounded-2xl" onClick={()=>setStep((s)=>Math.min(4, s+1))} disabled={!canContinue}>Continue <ChevronRight className="ml-2 h-4 w-4"/></Button>)}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

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
