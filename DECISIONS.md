
## 2026-04-19 — Phase 2 integration gap identified

- **Decision:** Declare Phase 2 *code complete* (all scorers and fixtures shipped) but NOT *integration complete*. Inbox generation and gold-graph generation do not share an entity model; `InboxManifest.entity_pool` is `list[str]` (names) while `generate_gold_graph` requires structured `PersonEntity`, `ProjectEntity`, `CrossReference` inputs. No code converts between the two.
- **Discovery:** End-to-end smoke test on main (after all Wave 2a merges) revealed the pipeline gap. All per-scorer unit tests pass because they construct synthetic structured entities directly rather than chaining from a real inbox.
- **Impact:** The engine has all ingestion-axis scorers but cannot yet be driven end-to-end from a submission. Phase 2 harness integration (reference submission + orchestration) is blocked until this gap closes.
- **Reasoning for Option A:**
  - Option B (write conversion glue now) would conflate "what the submission infers from the inbox" with "what the gold-graph's ground truth is" — they should be kept separate
  - Option C (refactor inbox to emit gold graph directly) is an architecture change requiring ADR-005 or ADR-001 amendment; too large for end-of-session work
  - Option A (log + defer to a tracked issue) is the honest, scoped response
- **Action:** BW-INTEG-2 drafted as the next issue. Phase 2 integration cannot start until INTEG-2 resolves.
- **Alternatives considered:** B and C above.

## 2026-04-19 — Phase 2 integration gap identified

- **Decision:** Declare Phase 2 *code complete* (all scorers and fixtures shipped) but NOT *integration complete*. Inbox generation and gold-graph generation do not share an entity model; `InboxManifest.entity_pool` is `list[str]` (names) while `generate_gold_graph` requires structured `PersonEntity`, `ProjectEntity`, `CrossReference` inputs. No code converts between the two.
- **Discovery:** End-to-end smoke test on main (after all Wave 2a merges) revealed the pipeline gap. All per-scorer unit tests pass because they construct synthetic structured entities directly rather than chaining from a real inbox.
- **Impact:** The engine has all ingestion-axis scorers but cannot yet be driven end-to-end from a submission. Phase 2 harness integration (reference submission + orchestration) is blocked until this gap closes.
- **Reasoning for Option A:**
  - Option B (write conversion glue now) would conflate "what the submission infers from the inbox" with "what the gold-graph's ground truth is" — they should be kept separate
  - Option C (refactor inbox to emit gold graph directly) is an architecture change requiring ADR-005 or ADR-001 amendment; too large for end-of-session work
  - Option A (log + defer to a tracked issue) is the honest, scoped response
- **Action:** BW-INTEG-2 drafted as the next issue. Phase 2 integration cannot start until INTEG-2 resolves.
- **Alternatives considered:** B and C above.
