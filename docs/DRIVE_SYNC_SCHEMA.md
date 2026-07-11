# Drive and API Sync Schema

The Google Drive dashboard and the LAW API use stable IDs rather than row positions.

| Drive tab | API table / object | Stable ID prefix |
|---|---|---|
| PROOF_DEBT_RESOLVER | proof_debts | PDR |
| ALIAS_ENTITY_REGISTRY | entity/alias records | ENT |
| SEARCH_RECEIPTS | search_runs | SR |
| RESOLUTION_EVENTS | resolution_events | RE / resolution |
| DEPENDENCY_GRAPH | dependency_edges | DG |
| CONTEXT_VERSIONS | context_versions | PSC |
| EXACT_INDEX_ROUTER | exact_index_entries | IDX |
| EVIDENCE_ATOMS | evidence_atoms | ATOM |
| AI_NEW_FINDINGS | ai_findings | AIF |
| ANSWER_LINEAGE | conclusions | CONC |
| CONCLUSION_INVALIDATION | invalidations | INV |
| HUMAN_REVIEW_QUEUE | review_decisions | HR |
| SOURCE_FAMILY_DEDUP | source_families | SF |
| DEAD_LEAD_EXCULPATORY | dead_leads | DL / EX |
| COVERAGE_GATE | coverage_rows | COV |
| NEXT_BEST_SEARCH | planning output | NBS |

## Sync rules

1. Never infer identity from row number.
2. Upsert only by stable ID.
3. Preserve created timestamps and append review/event history.
4. A Drive row may route to code but does not become native evidence.
5. A code-generated candidate or AI New Finding writes back as a candidate, questioned finding, or review event—never as source-closed proof.
6. Hash, revision, source species, proof tier, exact locator, open questions, and finding origin should survive round trips.
7. Conflicting source versions remain separate members of a source family.
8. Superseded conclusions and rejected findings remain visible and point to replacements when available.
9. Human confirmation must record reviewer identity, rationale, and required checks.
