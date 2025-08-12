import React, { useState, useEffect, useRef } from 'react'

const roles = ["Plaintiff","Defendant","Witness","Attorney","Bank","Contractor","Other"]

const defaultAnalysis = {
  parties: [
    { name: "Michael Bryce Jones", role: "Plaintiff", notes: "" },
    { name: "Suited Homes / Jeff Strong", role: "Contractor", notes: "" },
    { name: "Fortis Private Bank", role: "Bank", notes: "" },
    { name: "Colby Peterson", role: "Contractor", notes: "" }
  ],
  tags: ["construction","bank-draws","fraud-investigation","Utah","2018-2019"],
  description: "Auto-summary: Residential construction dispute with disputed draws and alleged forged signatures. Core parties: homeowner, builder, lender."
}

const initialDraft = {
  caseName: '',
  caseNumber: '',
  jurisdiction: '',
  filingDate: '',
  description: '',
  parties: [],
  tags: [],
  files: []
}

export default function CaseProfileApp() {
  const [view, setView] = useState('list')
  const [cases, setCases] = useState([])
  const [currentCase, setCurrentCase] = useState(null)
  const [draft, setDraft] = useState(initialDraft)
  const [step, setStep] = useState(0)
  const [messages, setMessages] = useState([])
  const [tasks, setTasks] = useState([])
  const [msgForm, setMsgForm] = useState({ text: '', author: '', internal: false })
  const [taskForm, setTaskForm] = useState({ text: '', dueAt: '', assignedTo: '' })
  const fileInput = useRef(null)

  useEffect(() => {
    if (view === 'list') {
      fetch('/api/cases').then(r => r.json()).then(setCases)
    }
  }, [view])

  useEffect(() => {
    if (view === 'detail' && currentCase) {
      fetch(`/api/cases/${currentCase.id}/messages`).then(r => r.json()).then(setMessages)
      fetch(`/api/cases/${currentCase.id}/tasks`).then(r => r.json()).then(setTasks)
    }
  }, [view, currentCase])

  function resetDraft() {
    setDraft(initialDraft)
    setStep(0)
  }

  function openCase(c) {
    setCurrentCase(c)
    setView('detail')
  }

  function StepBasics() {
    return (
      <div>
        <h2>Basics</h2>
        <input placeholder="Case Name" value={draft.caseName} onChange={e => setDraft({ ...draft, caseName: e.target.value })} />
        <input placeholder="Case Number" value={draft.caseNumber} onChange={e => setDraft({ ...draft, caseNumber: e.target.value })} />
        <input placeholder="Jurisdiction" value={draft.jurisdiction} onChange={e => setDraft({ ...draft, jurisdiction: e.target.value })} />
        <input type="date" value={draft.filingDate} onChange={e => setDraft({ ...draft, filingDate: e.target.value })} />
        <textarea placeholder="Description" value={draft.description} onChange={e => setDraft({ ...draft, description: e.target.value })} />
        <div>
          <button disabled>Back</button>
          <button onClick={() => setStep(step + 1)} disabled={!draft.caseName}>Continue</button>
        </div>
      </div>
    )
  }

  function StepParties() {
    const addParty = () => setDraft(d => ({ ...d, parties: [...d.parties, { name: '', role: roles[0], notes: '' }] }))
    const updateParty = (i, field, value) => {
      const parties = draft.parties.map((p, idx) => idx === i ? { ...p, [field]: value } : p)
      setDraft({ ...draft, parties })
    }
    const removeParty = (i) => {
      const parties = draft.parties.filter((_, idx) => idx !== i)
      setDraft({ ...draft, parties })
    }
    const [tagInput, setTagInput] = useState('')
    const addTag = () => {
      if (tagInput) {
        setDraft(d => ({ ...d, tags: [...d.tags, tagInput] }))
        setTagInput('')
      }
    }
    return (
      <div>
        <h2>Parties & Roles</h2>
        <button onClick={addParty}>Add Party</button>
        <table>
          <thead><tr><th>Name</th><th>Role</th><th>Notes</th><th></th></tr></thead>
          <tbody>
            {draft.parties.map((p, i) => (
              <tr key={i}>
                <td><input value={p.name} onChange={e => updateParty(i, 'name', e.target.value)} /></td>
                <td>
                  <select value={p.role} onChange={e => updateParty(i, 'role', e.target.value)}>
                    {roles.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td><input value={p.notes} onChange={e => updateParty(i, 'notes', e.target.value)} /></td>
                <td><button onClick={() => removeParty(i)}>X</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div>
          <input placeholder="tag" value={tagInput} onChange={e => setTagInput(e.target.value)} />
          <button onClick={addTag}>Add Tag</button>
          <div>{draft.tags.map((t, i) => <span key={i}>{t} </span>)}</div>
        </div>
        <div>
          <button onClick={() => setStep(step - 1)}>Back</button>
          <button onClick={() => setStep(step + 1)}>Continue</button>
        </div>
      </div>
    )
  }

  function StepDocuments() {
    const onDrop = e => {
      e.preventDefault()
      handleFiles(e.dataTransfer.files)
    }
    const onChange = e => handleFiles(e.target.files)
    const analyze = () => {
      setDraft(d => ({
        ...d,
        parties: d.parties.length ? d.parties : defaultAnalysis.parties,
        tags: d.tags.length ? d.tags : defaultAnalysis.tags,
        description: d.description || defaultAnalysis.description
      }))
    }
    return (
      <div>
        <h2>Documents</h2>
        <div className="drag-area" onDragOver={e => e.preventDefault()} onDrop={onDrop} onClick={() => fileInput.current.click()}>
          Drag & drop or click to upload
          <input type="file" multiple style={{ display: 'none' }} ref={fileInput} onChange={onChange} />
        </div>
        <ul>
          {draft.files.map((f, i) => <li key={i}>{f.name} {f.sha256}</li>)}
        </ul>
        <button onClick={analyze}>Analyze uploads</button>
        <div>
          <button onClick={() => setStep(step - 1)}>Back</button>
          <button onClick={() => setStep(step + 1)}>Continue</button>
        </div>
      </div>
    )
  }

  function StepReview() {
    const create = async () => {
      await fetch('/api/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft)
      })
      resetDraft()
      setView('list')
    }
    return (
      <div>
        <h2>Review & Create</h2>
        <pre>{JSON.stringify(draft, null, 2)}</pre>
        <div>
          <button onClick={() => setStep(step - 1)}>Back</button>
          <button onClick={create}>Create Case</button>
        </div>
      </div>
    )
  }

  function handleFiles(files) {
    Array.from(files).forEach(async file => {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/scan-upload', { method: 'POST', body: form })
      const json = await res.json()
      setDraft(d => ({ ...d, files: [...d.files, json] }))
    })
  }

  async function submitMessage(e) {
    e.preventDefault()
    const res = await fetch(`/api/cases/${currentCase.id}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(msgForm)
    })
    const json = await res.json()
    setMessages(m => [...m, json])
    setMsgForm({ text: '', author: '', internal: false })
  }

  async function submitTask(e) {
    e.preventDefault()
    const res = await fetch(`/api/cases/${currentCase.id}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(taskForm)
    })
    const json = await res.json()
    setTasks(t => [...t, json])
    setTaskForm({ text: '', dueAt: '', assignedTo: '' })
  }

  function renderList() {
    return (
      <div>
        <h1>My Cases</h1>
        <button onClick={() => { resetDraft(); setView('create') }}>+ New Case</button>
        {cases.length === 0 ? <p>No cases yet</p> : (
          <ul>
            {cases.map(c => <li key={c.id}><a href="#" onClick={() => openCase(c)}>{c.caseName}</a></li>)}
          </ul>
        )}
      </div>
    )
  }

  function renderDetail() {
    return (
      <div>
        <button onClick={() => setView('list')}>Back</button>
        <h2>{currentCase.caseName}</h2>
        <section>
          <h3>Basics</h3>
          <p>Case Number: {currentCase.caseNumber}</p>
          <p>Jurisdiction: {currentCase.jurisdiction}</p>
          <p>Filing Date: {currentCase.filingDate}</p>
          <p>{currentCase.description}</p>
        </section>
        <section>
          <h3>Parties</h3>
          <ul>
            {currentCase.parties.map((p, i) => <li key={i}>{p.name} - {p.role} {p.notes && `(${p.notes})`}</li>)}
          </ul>
          <p>Tags: {currentCase.tags.join(', ')}</p>
        </section>
        <section>
          <h3>Files</h3>
          <ul>
            {currentCase.files.map((f, i) => <li key={i}>{f.name} ({f.mime || f.type}) {f.sha256}</li>)}
          </ul>
        </section>
        <section>
          <h3>Messages</h3>
          <ul>
            {messages.map(m => <li key={m.id}>{m.at} {m.author}: {m.text}</li>)}
          </ul>
          <form onSubmit={submitMessage}>
            <input placeholder="Author" value={msgForm.author} onChange={e => setMsgForm({ ...msgForm, author: e.target.value })} />
            <input placeholder="Message" value={msgForm.text} onChange={e => setMsgForm({ ...msgForm, text: e.target.value })} />
            <label><input type="checkbox" checked={msgForm.internal} onChange={e => setMsgForm({ ...msgForm, internal: e.target.checked })} /> Internal</label>
            <button type="submit">Add Message</button>
          </form>
        </section>
        <section>
          <h3>Tasks</h3>
          <ul>
            {tasks.map(t => <li key={t.id}>{t.text} (due {t.dueAt})</li>)}
          </ul>
          <form onSubmit={submitTask}>
            <input placeholder="Task" value={taskForm.text} onChange={e => setTaskForm({ ...taskForm, text: e.target.value })} />
            <input type="date" value={taskForm.dueAt} onChange={e => setTaskForm({ ...taskForm, dueAt: e.target.value })} />
            <input placeholder="Assigned To" value={taskForm.assignedTo} onChange={e => setTaskForm({ ...taskForm, assignedTo: e.target.value })} />
            <button type="submit">Add Task</button>
          </form>
        </section>
      </div>
    )
  }

  const wizardSteps = [<StepBasics key={0} />, <StepParties key={1} />, <StepDocuments key={2} />, <StepReview key={3} />]

  if (view === 'create') {
    return wizardSteps[step]
  }
  if (view === 'detail' && currentCase) {
    return renderDetail()
  }
  return renderList()
}
