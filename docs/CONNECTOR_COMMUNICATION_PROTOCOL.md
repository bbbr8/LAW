# Source-Bound Connector Communication Protocol

## Purpose

The case system previously had strong individual components but no single durable communication contract between them. This protocol adds an auditable outbox and acknowledgement layer for:

- Google Drive — native evidence vault and controlling source registry;
- Gmail — native communication and EML/attachment provenance lane;
- Dropbox — legacy source/cache pointer and access-history lane;
- Case API — orchestration, proof-debt, evidence-atom, review, and transport state;
- Hugging Face — local/private derivative retrieval, reranking, classification, and candidate generation;
- Figma/FigJam — editable visual projection of normalized nodes, edges, proof gaps, and review state;
- GitHub — public-safe code, schemas, tests, synthetic fixtures, and reproducibility history.

The connector bus does not replace the connected services. It records what was routed, why it was routed, what source controlled it, what privacy mode applied, whether the target received it, and whether the target acknowledged it.

## Core evidence rule

Native evidence stays in its controlling source system. Connector messages may carry:

1. `source_pointer`
2. `metadata`
3. `redacted_derivative`
4. `control_record`
5. `visual_projection`
6. `model_candidate`
7. `acknowledgement`

They may not carry native file bytes, attachment bytes, base64 evidence, access tokens, passwords, secrets, or hidden credential material.

## Envelope fields

Every cross-system message receives:

- stable message ID;
- case ID;
- correlation and causation IDs;
- SHA-256 content digest;
- deterministic idempotency key;
- source and target systems;
- event, object type, and stable object ID;
- intent and operation;
- source status, proof tier, locator, hash, revision, and source-family ID;
- privacy, privilege, payload mode, and processing scope;
- explicit mutation authorization when required;
- promotion-block status and reasons;
- bounded structured payload.

The JSON contract is in `schemas/connector-envelope.schema.json`.

## System-specific rules

### Google Drive

- Remains the native evidence plane.
- Connector writes require explicit authorization with author, time, and narrow scope.
- No automation may silently move, rename, delete, overwrite, or materially alter native case evidence.

### Gmail

- Routes message IDs, thread IDs, full-header/EML availability, attachment IDs, hashes, dates, actors, and source locators.
- Sending, deleting, archiving, forwarding, or labeling requires explicit authorization.
- Message bodies are not sent to GitHub or Figma through the connector bus.

### Hugging Face

- Accepts only local, private-endpoint, or private-space work.
- Receives bounded redacted derivatives, metadata, source pointers, or control records.
- Restricted case material may be sent only as a pointer or metadata record.
- Outputs return as `model_candidate` and remain promotion blocked until source and human-review gates are satisfied.

### Figma / FigJam

- Receives `visual_projection`, metadata, source pointers, or control records.
- Each node and edge should retain stable ID, source status, native locator or explicit proof debt, direct-injury/context classification, supersession state, and review owner.
- Visuals are derivative review objects, not independent evidence.

### GitHub

- Receives only public-safe source pointers, metadata, control records, and acknowledgements.
- Raw case text, OCR, transcripts, message bodies, native bytes, and privileged material are blocked.
- GitHub continues to hold code, schemas, tests, synthetic fixtures, configuration, and change history—not the litigation evidence vault.

### Dropbox

- Treated as a legacy source/cache pointer lane until exact account, folder, access, and custody records establish a stronger role.
- Connector messages retain the original item locator and hash rather than treating a copied file as independent corroboration.

## Reliability model

### Transactional outbox

Creating a connector message and its per-target delivery rows occurs in one SQLite transaction. Each target receives an independent delivery record.

### Idempotency

The idempotency key is a SHA-256 digest of the case, source, targets, event, object identity, source revision identity, and payload digest. Re-submitting the same event returns the existing message rather than creating false duplicate corroboration.

### Delivery states

`pending -> in_progress -> delivered -> acknowledged`

Failure paths:

- `in_progress -> failed -> in_progress`
- `pending|in_progress|failed -> dead_letter`
- `pending|failed|dead_letter -> skipped`

Attempts, receipts, failure reasons, delivery times, and acknowledgement times remain in the delivery record.

### Checkpoints

Each connector/stream pair has a stable checkpoint ID and stores its cursor, watermark, and source revision. This supports incremental Drive revision sync, Gmail pagination, Figma export refresh, Hugging Face job return, GitHub control updates, and Dropbox legacy indexing without restarting the entire corpus.

### Health

The health endpoint reports, per connector:

- source messages;
- queued deliveries;
- pending, delivered, acknowledged, failed, and dead-letter counts;
- promotion-blocked items;
- oldest pending age;
- last acknowledgement;
- checkpoint count and last checkpoint time.

## API

### Capabilities

- `GET /api/connectors`

### Outbox

- `POST /api/cases/:id/connector-messages`
- `GET /api/cases/:id/connector-messages`
- `GET /api/cases/:id/connector-messages/:messageId`

### Delivery workers

- `GET /api/cases/:id/connector-deliveries`
- `POST /api/cases/:id/connector-deliveries/claim`
- `POST /api/cases/:id/connector-deliveries/:deliveryId/transition`

### Incremental synchronization

- `POST /api/cases/:id/connector-checkpoints`
- `GET /api/cases/:id/connector-checkpoints`

### Monitoring

- `GET /api/cases/:id/connector-health`

## Drive-to-Figma example

```json
{
  "sourceSystem": "google_drive",
  "targets": ["case_api", "figma"],
  "eventType": "source.revision_observed",
  "objectType": "evidence_source",
  "objectId": "SRC-DRAW-003",
  "intent": "route",
  "sourceStatus": "native_source",
  "proofTier": "F1",
  "nativeLocator": "drive:file:FILE_ID#revision:REVISION_ID",
  "sourceHash": "sha256:...",
  "revision": "REVISION_ID",
  "payloadMode": "visual_projection",
  "sensitivity": "confidential",
  "payload": {
    "stableNodeId": "RREG-EP-03",
    "label": "Draw 3 authorization and category-treatment lane",
    "sourceManifestId": "SM-RREG-EP-03",
    "bridgeRecordNeeded": "Native borrower authorization and lender workflow record"
  }
}
```

The visual is synchronized, but it remains derivative. Its source locator and promotion state travel with it.

## Private Hugging Face example

```json
{
  "sourceSystem": "case_api",
  "targets": ["hugging_face"],
  "eventType": "retrieval.rerank_requested",
  "objectType": "search_run",
  "objectId": "SR-2026-07-11-001",
  "intent": "analyze",
  "sourceStatus": "source_derived",
  "payloadMode": "redacted_derivative",
  "processingScope": "local",
  "sensitivity": "confidential",
  "payload": {
    "queryId": "Q-001",
    "candidateIds": ["PASS-001", "PASS-002"],
    "redactionProfile": "case-private-v1",
    "model": "BAAI/bge-reranker-v2-m3"
  }
}
```

The returned ranking should be routed back as `model_candidate`, preserving candidate IDs and scores while remaining promotion blocked.
