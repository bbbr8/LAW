import { open } from 'sqlite'
import sqlite3 from 'sqlite3'

export async function initDb() {
  const db = await open({ filename: './server/database.sqlite', driver: sqlite3.Database })

  await db.exec(`
    CREATE TABLE IF NOT EXISTS cases (
      id TEXT PRIMARY KEY,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS proof_debts (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS evidence_sources (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS search_runs (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS resolution_events (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      debtId TEXT,
      evidenceId TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dependency_edges (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      fromId TEXT NOT NULL,
      toId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_messages_case ON messages(caseId);
    CREATE INDEX IF NOT EXISTS idx_tasks_case ON tasks(caseId);
    CREATE INDEX IF NOT EXISTS idx_proof_debts_case ON proof_debts(caseId);
    CREATE INDEX IF NOT EXISTS idx_evidence_sources_case ON evidence_sources(caseId);
    CREATE INDEX IF NOT EXISTS idx_search_runs_case ON search_runs(caseId);
    CREATE INDEX IF NOT EXISTS idx_resolution_events_case ON resolution_events(caseId);
    CREATE INDEX IF NOT EXISTS idx_resolution_events_debt ON resolution_events(debtId);
    CREATE INDEX IF NOT EXISTS idx_dependency_edges_case ON dependency_edges(caseId);
    CREATE INDEX IF NOT EXISTS idx_dependency_edges_from ON dependency_edges(fromId);
  `)

  return db
}
