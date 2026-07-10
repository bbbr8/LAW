export async function ensureAccountingSchema(db) {
  await db.exec(`
    CREATE TABLE IF NOT EXISTS money_events (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      obligationId TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS accounting_obligations (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      reconciliationStatus TEXT,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS accounting_reconciliation_runs (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS final_balance_controls (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      data TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS source_requests (
      id TEXT PRIMARY KEY,
      caseId TEXT NOT NULL,
      status TEXT,
      data TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_money_events_case ON money_events(caseId);
    CREATE INDEX IF NOT EXISTS idx_money_events_obligation ON money_events(obligationId);
    CREATE INDEX IF NOT EXISTS idx_accounting_obligations_case ON accounting_obligations(caseId);
    CREATE INDEX IF NOT EXISTS idx_accounting_obligations_status ON accounting_obligations(reconciliationStatus);
    CREATE INDEX IF NOT EXISTS idx_accounting_reconciliation_runs_case ON accounting_reconciliation_runs(caseId);
    CREATE INDEX IF NOT EXISTS idx_final_balance_controls_case ON final_balance_controls(caseId);
    CREATE INDEX IF NOT EXISTS idx_source_requests_case ON source_requests(caseId);
    CREATE INDEX IF NOT EXISTS idx_source_requests_status ON source_requests(status);
  `)
}
