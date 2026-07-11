# First-Person Statement and Recollection Mini-Learning

## Purpose

The user has supplied years of statements, recollections, corrections, event-time understandings, authored emails, declarations, and source-driven refinements. Those statements are valuable because they identify:

- what the Borrower did, knew, received, understood, authorized, or did not authorize;
- what the Borrower remembers another actor saying;
- which later records changed or sharpened the Borrower’s terminology;
- which amounts, dates, and classifications the Borrower later corrected;
- which native records would confirm, limit, or falsify the recollection.

The system must preserve that value without turning memory into independent proof of another person’s conduct or intent.

## Core rule

A first-person statement is a source object with a defined scope.

It may directly establish the speaker’s present statement and, depending on oath/authentication, what the speaker says they did, knew, received, understood, or authorized. It does not automatically establish:

- that another person made the recalled statement;
- that a disputed document is forged or authentic;
- that money was applied to a particular obligation;
- another actor’s knowledge or intent;
- final damages or legal liability.

Those issues remain tied to native records, sworn testimony, reproducible accounting, authentication, and human review.

## Statement dimensions

Each statement is classified as one of:

- `self_action`
- `self_knowledge`
- `self_authorization`
- `self_receipt_timing`
- `self_understanding`
- `accounting_correction`
- `recollection_of_other_statement`
- `recollection_of_event`
- `interpretation`

This prevents the system from treating “I did not sign this” the same as “I remember being told this would be reimbursed” or “I believe this amount was misapplied.”

## Source classes

Supported source classes are:

- `first_person_recollection`
- `first_person_self_fact`
- `user_correction`
- `sworn_first_person`
- `user_authored_source`
- `user_authored_source_with_embedded_quote`
- `interpretation`

The exact language is preserved. A normalized statement may be added for retrieval, but it never replaces the original wording.

## Versioning and corrections

A correction creates a new version under the same canonical statement ID.

The system compares:

- exact identifiers such as dates, amounts, checks, invoices, loans, accounts, and Bates labels;
- statement dimension;
- source class;
- event period;
- topic assignment;
- language similarity.

Material changes create an open conflict record. The prior version remains visible. This is especially important for owner-funding totals, returned funds, internal transfers, draw amounts, dates, and event-time characterizations.

## Topic-specific mini-learning

A statement can create one or more topic-learning examples. Current intended topics include:

- inducement and transaction substitution;
- temporary advances, reimbursement, and customer credit;
- baseline scope and change-order analysis;
- draw authorization and signature mechanics;
- owner visibility and information asymmetry;
- late document disclosure and first receipt;
- owner-funding source-of-funds corrections;
- event-time state of mind and language evolution;
- informed consent and short-message context;
- cross-project contamination and identity firewalls.

Each learning example contains:

- stable statement and topic IDs;
- source class and statement dimension;
- exact-key features;
- positive-example role;
- hard negatives and collision examples;
- required record features;
- expected search route or classification;
- promotion block.

## Hugging Face boundary

The default Hugging Face projection excludes exact statement language. It contains stable IDs, topic labels, source class, statement dimension, event period, exact-key features, language digest, hard negatives, and expected routes.

Exact language may be included only when an explicitly approved private/local workflow requests it. The resulting model output is still a candidate and cannot independently promote a statement.

## Evidence matching

A candidate source is scored against a statement using:

- exact identifier overlap;
- topic overlap;
- lexical similarity;
- native/sworn source posture.

The result is one of:

- `strong_source_candidate`
- `review_candidate`
- `weak_or_collision_candidate`

All remain promotion blocked until identity, observer-time, contrary-evidence, and human-review checks are completed.

## Promotion scope

A self-limited statement may become:

`Human-Confirmed First-Person Fact — Limited to Speaker Knowledge`

only after:

- human review;
- identity-firewall review;
- observer-time review;
- contrary-evidence review;
- native or sworn source support where applicable.

A recollection about another actor may become source-supported, but attribution and intent remain separate questions.

## API

### Configuration

- `GET /api/recollection-learning/config`

### Statements

- `POST /api/cases/:id/user-statements`
- `GET /api/cases/:id/user-statements`
- `GET /api/cases/:id/user-statements/:statementId`
- `POST /api/cases/:id/user-statements/:statementId/revise`

### Conflicts and source closure

- `GET /api/cases/:id/statement-conflicts`
- `POST /api/cases/:id/user-statements/:statementId/source-links`
- `POST /api/cases/:id/user-statements/:statementId/evaluate-source`

### Topic learning

- `POST /api/cases/:id/user-statements/:statementId/topic-example`
- `GET /api/cases/:id/topic-learning-examples`
- `GET /api/cases/:id/user-statements/:statementId/hf-projection`

## Drive control register

The initial case-specific control register is:

`00_FIRST_PERSON_STATEMENT_RECOLLECTION_MINI_LEARNING_REGISTER_2026-07-11`

It contains:

- exact statement IDs;
- topic assignments;
- source posture;
- native-record needs;
- competing explanations;
- falsifiers;
- accounting conflicts;
- source-closure priorities.

Drive remains the case evidence/control plane. GitHub contains only public-safe code, schemas, tests, and methodology.
