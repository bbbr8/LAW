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

    CREATE TABLE IF NOT EXISTS exact_index_entries (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      indexType TEXT NOT NULL,
      normalizedKey TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS evidence_atoms (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      sourceId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS conclusions (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      currentStatus TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ai_findings (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      currentStatus TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS invalidations (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      impactedConclusionId TEXT NOT NULL,
      triggerId TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS review_decisions (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      debtId TEXT,
      eventId TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS source_families (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      canonicalSourceId TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS context_versions (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      status TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dead_leads (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      disposition TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS coverage_rows (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      searchRunId TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS connector_messages (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      sourceSystem TEXT NOT NULL,
      idempotencyKey TEXT NOT NULL,
      createdAt TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS connector_deliveries (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      messageId TEXT NOT NULL,
      targetSystem TEXT NOT NULL,
      status TEXT NOT NULL,
      updatedAt TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS connector_checkpoints (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      connectorId TEXT NOT NULL,
      stream TEXT NOT NULL,
      updatedAt TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS user_statements (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      canonicalId TEXT NOT NULL,
      version INTEGER NOT NULL,
      isCurrent INTEGER NOT NULL DEFAULT 1,
      currentStatus TEXT NOT NULL,
      recordDigest TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS statement_conflicts (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      canonicalId TEXT NOT NULL,
      status TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS statement_source_links (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      statementId TEXT NOT NULL,
      sourceId TEXT,
      createdAt TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS topic_learning_examples (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      statementId TEXT NOT NULL,
      exampleType TEXT NOT NULL,
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
    CREATE INDEX IF NOT EXISTS idx_exact_index_case_type_key ON exact_index_entries(caseId, indexType, normalizedKey);
    CREATE INDEX IF NOT EXISTS idx_evidence_atoms_case ON evidence_atoms(caseId);
    CREATE INDEX IF NOT EXISTS idx_evidence_atoms_source ON evidence_atoms(sourceId);
    CREATE INDEX IF NOT EXISTS idx_conclusions_case ON conclusions(caseId);
    CREATE INDEX IF NOT EXISTS idx_conclusions_status ON conclusions(currentStatus);
    CREATE INDEX IF NOT EXISTS idx_ai_findings_case ON ai_findings(caseId);
    CREATE INDEX IF NOT EXISTS idx_ai_findings_status ON ai_findings(currentStatus);
    CREATE INDEX IF NOT EXISTS idx_invalidations_case ON invalidations(caseId);
    CREATE INDEX IF NOT EXISTS idx_invalidations_conclusion ON invalidations(impactedConclusionId);
    CREATE INDEX IF NOT EXISTS idx_review_decisions_debt ON review_decisions(debtId);
    CREATE INDEX IF NOT EXISTS idx_source_families_case ON source_families(caseId);
    CREATE INDEX IF NOT EXISTS idx_context_versions_case ON context_versions(caseId);
    CREATE INDEX IF NOT EXISTS idx_dead_leads_case ON dead_leads(caseId);
    CREATE INDEX IF NOT EXISTS idx_coverage_search_run ON coverage_rows(searchRunId);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_connector_messages_case_idempotency
      ON connector_messages(caseId, idempotencyKey);
    CREATE INDEX IF NOT EXISTS idx_connector_messages_case_created
      ON connector_messages(caseId, createdAt);
    CREATE INDEX IF NOT EXISTS idx_connector_messages_source
      ON connector_messages(caseId, sourceSystem);
    CREATE INDEX IF NOT EXISTS idx_connector_deliveries_queue
      ON connector_deliveries(caseId, targetSystem, status, updatedAt);
    CREATE INDEX IF NOT EXISTS idx_connector_deliveries_message
      ON connector_deliveries(caseId, messageId);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_connector_checkpoints_stream
      ON connector_checkpoints(caseId, connectorId, stream);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_user_statements_case_digest
      ON user_statements(caseId, recordDigest);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_user_statements_canonical_version
      ON user_statements(caseId, canonicalId, version);
    CREATE INDEX IF NOT EXISTS idx_user_statements_current
      ON user_statements(caseId, isCurrent, canonicalId);
    CREATE INDEX IF NOT EXISTS idx_user_statements_status
      ON user_statements(caseId, currentStatus);
    CREATE INDEX IF NOT EXISTS idx_statement_conflicts_case_status
      ON statement_conflicts(caseId, status);
    CREATE INDEX IF NOT EXISTS idx_statement_source_links_statement
      ON statement_source_links(caseId, statementId, createdAt);
    CREATE INDEX IF NOT EXISTS idx_topic_learning_examples_statement
      ON topic_learning_examples(caseId, statementId, exampleType);
  `)

  return db
}
