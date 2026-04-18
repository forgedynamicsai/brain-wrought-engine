# DECISIONS

Running log of meaningful project choices. Append-only.

Format: date, decision, reasoning, alternative considered.

---

## 2026-04-18 — Project founded

- **Decision:** Launch Brain-Wrought as independent open benchmark for personal AI knowledge systems
- **Reasoning:** Gap in the landscape (no full 3-axis personal-brain benchmark), Berkeley RDI exploit paper creates peak attention moment, developmentally valuable for Arron's GS-13+ transition into federal AI evaluation work
- **Alternatives:** Continue Forge Dynamics; ship WroughtAI consulting platform; focus on Management Gap content
- **Paused:** Forge Dynamics (can resume post-PCS with Brain-Wrought infrastructure as base)

## 2026-04-18 — Scope: three-axis, not four or five

- **Decision:** v1 covers retrieval + ingestion + assistant. Maintenance axis deferred to v2; privacy deferred to v1.1 (integrate PrivacyBench).
- **Reasoning:** Warpspeed timeline requires scope discipline. Three axes is already the broadest coverage in this space.
- **ADR:** ADR-001

## 2026-04-18 — Scope: retrieval-first public ship

- **Decision:** Ship retrieval axis publicly at week 2-3; ingestion at week 5-6; assistant + v1 at week 9-10.
- **Reasoning:** Plants flag earlier, creates 3 public moments instead of 1, lets community engagement start during build
- **Alternatives:** Single v1 launch at week 9-12 (standard approach)

## 2026-04-18 — Architecture: Thin Harness / Fat Skills / Fat Code / Sealed Artifacts

- **Decision:** Four-layer decomposition across four repos (3 public, 1 private)
- **Reasoning:** Garry Tan's Thin Harness / Fat Skills pattern + Berkeley-exploit defense via Sealed Artifacts
- **ADR:** ADR-003

## 2026-04-18 — Judge panel: 3 judges (Sonnet 4.6 + Opus 4.7 + GPT-5.4)

- **Decision:** Majority vote with bootstrap CI; rubrics sealed and rotated quarterly
- **Reasoning:** Cross-vendor diversity reduces correlated failure; sealed rubrics resist Berkeley-style over-fitting
- **Alternatives:** Single judge (rejected — vulnerable); 5-judge (rejected — cost-benefit); human judge (rejected for v1 — doesn't scale)
- **ADR:** ADR-002

## 2026-04-18 — Model routing: Opus for architecture, Sonnet for build, Haiku batch for fixtures

- **Decision:** Opus 4.7 for ADRs and rubric design; Sonnet 4.6 as Claude Code daily driver; Haiku 4.5 batch for all synthetic fixture generation
- **Reasoning:** Capability/cost optimization. Opus 4.7 35% tokenizer inflation is a real gotcha — test before committing to 4.7 for repetitive work
- **Cost impact:** ~$150-200 total build cost vs. ~$700+ if Opus-everywhere

## 2026-04-18 — No monetization infrastructure

- **Decision:** Zero Stripe/billing tables/enterprise tier. Arxiv preprint and community adoption are the deliverables.
- **Reasoning:** Arron is federal employee, can't earn outside income. Developmental/profile-building is the goal.
- **Scope saved:** ~15-20 hours removed from build

## 2026-04-18 — Name: brain-wrought

- **Decision:** `brain-wrought` as project name and GitHub repo names
- **Reasoning:** "Wrought" = deliberately shaped by skilled labor; nods to WroughtAI without commercial attribution; unGoogled enough to own SEO
- **Alternatives considered:** brain-eval, brainbench, vaultbench, wroughtai-brain-eval

## 2026-04-18 — Neutral positioning (no WroughtAI attribution)

- **Decision:** Brain-Wrought presents as independent, not under WroughtAI brand
- **Reasoning:** Federal ethics + credibility. Third-party benchmark cred is stronger when no commercial entity is attached.
- **Alternatives:** Under WroughtAI brand (rejected — commercial affiliation weakens neutrality claim)

## 2026-04-18 — Reproducibility baked in from day one

- **Decision:** Docker, pinned versions, deterministic seeds, public CI all present in Phase 0 scaffolding
- **Reasoning:** Retrofit cost >> build-in cost; academic and community reviewers weight reproducibility heavily
- **ADR:** ADR-004

## 2026-04-19 — Repos hosted under forgedynamicsai GitHub org

- **Decision:** Brain-Wrought repos live under github.com/forgedynamicsai, not a standalone brain-wrought org
- **Reasoning:** Practical — existing org, no new admin overhead. No commercial activity (no revenue, no marketing, no licensing) so ethics optics remain clean. "Independent benchmark" claim holds as long as Forge Dynamics doesn't commercialize Brain-Wrought.
- **Constraint added:** If Forge Dynamics ever takes outside revenue, Brain-Wrought must be transferred to a neutral org before any Forge Dynamics commercial announcement.
- **Action item:** Schedule Post Ethics Counselor check-in before Phase 1 public launch to confirm optics

## 2026-04-19 — CORRECTION: Target venue strategy

- **Decision:** Primary venues are arxiv preprint (on v1 launch) + NeurIPS 2027 Evaluations & Datasets Track. Not Berkeley AgentX-AgentBeats Phase 2.
- **Reasoning:** Initial planning incorrectly identified AgentX Phase 2 as a benchmark-submission venue with prize eligibility. AgentX-AgentBeats Phase 2 (March-May 2026) is actually a **competing-agent tournament** — teams build purple agents to score against the green-agent benchmarks from Phase 1. The benchmark-submission window was Phase 1, which closed January 15, 2026. Brain-Wrought was never eligible for the June 20 deadline because that deadline didn't exist.
- **Venue re-targeting:**
  - Arxiv preprint on v1 launch (summer 2026) — primary independent artifact, no gatekeeper
  - NeurIPS 2027 ED Track (abstract ~May 2027, conference Dec 2027) — formal academic venue; fits scope exactly ("rigorous reproduction, auditing, and stress-testing of prior evaluations")
  - Independent public launch (blog, X, HN, Garry Tan DM, Mem0/Cognee outreach) — community-side flag-planting
  - NOT targeting: NeurIPS 2026 ED (May 6, 2026 deadline too tight for 8-10 hrs/week capacity); ICLR 2027 (deadline falls near Sept 2026 PCS; too risky); AgentX next cycle Phase 1 (likely Fall 2026 opening, collides with PCS)
- **What doesn't change:** Architecture, three-axis framework, warpspeed tempo, reproducibility discipline, Berkeley-proof design, skill reuse map, cost model. The *artifact* is unchanged; only the submission target shifts.
- **What does change:**
  - Phase 4 drops AgentX submission package deliverables; adds arxiv preprint polish
  - v1 public target language shifts from "by June 20" to "summer 2026 (approximately Jun-Jul)"
  - RISKS.md R-01 likelihood increases (no external forcing function); R-15 added (academic-momentum decay over 10-month gap to NeurIPS)
  - No prize money target. Prize eligibility remains permissible in principle if a suitable venue appears, but current plan doesn't depend on any prize.
- **Affected files updated:** PROJECT_INSTRUCTIONS.md, PROJECT_CONTEXT.md, BUILD_PLAN.md, RISKS.md, DECISIONS.md (this entry). All updates are v2, dated 2026-04-19.

## 2026-04-19 — Supabase scope: brain_wrought schema lives inside wroughtai project (through v1)

- **Decision:** Keep `brain_wrought` schema inside the existing `wroughtai` Supabase project through v1 launch
- **Reasoning:** Cost savings, ops simplicity, RLS discipline already in place. Blast radius to WealthAgent is low given schema separation.
- **Revisit conditions:** If Brain-Wrought grows to independent operational scale (100+ submissions/month), or if WealthAgent billing attribution becomes confusing, or if any cross-schema incident reveals coupling we didn't anticipate
- **Alternative:** Dedicated `brain-wrought` Supabase project (rejected for now — cost/benefit unfavorable at current scale)

## 2026-04-19 — BW-002 and BW-004 split into "a" scaffolding + "b" semantic completeness

- **Decision:** When Wave 1/2 agents under-scoped BW-002 and BW-004 relative to the WAVE_1_ISSUES.md spec, the fix was to rename the in-flight PRs as `[BW-002a]` and `[BW-004a]` (honest skeletons), merge them as-is, and open follow-up issues `[BW-002b]` (#7) and `[BW-004b]` (#6) to cover the missing semantic work.
- **Reasoning:** The agents' first-pass code was correct scaffolding even though it wasn't the full spec. Splitting preserves real work while being honest about what's complete. Rejecting and respawning would throw away vetted tests and data models.
- **Constraint added:** BW-006 (reference submission) must NOT unblock on BW-002a + BW-004a alone. It requires BW-002b's typed queries + non-title query text AND BW-004b's self-eval Docker wiring. Otherwise BW-006's naive grep baseline scores ~100% trivially against degenerate qrels, and the leaderboard has no real signal.
- **Pattern worth watching:** If BW-006 also ships under-scoped (e.g., Dockerfile builds but doesn't actually run, or runs but only against stub qrels), apply the same a/b split.

## 2026-04-19 — nDCG floating-point clamp (BW-003 PR review fix)

- **Decision:** nDCG output clamped via `min(dcg/idcg, 1.0)` to handle IEEE 754 ULP drift above 1.0
- **Reasoning:** Standard defensive pattern used in TREC eval, pytrec_eval, and production IR systems. Without the clamp, a rare ULP overflow pushes nDCG from 1.0000000000 to 1.0000000001 and downstream code that asserts `0 <= ndcg <= 1` breaks.
- **Note:** Code comment added explaining why the clamp exists, so future auditors don't think it's masking a real scoring bug

---

*(Append new decisions below. Never edit past entries — add a superseding entry if direction changes.)*

---

*v2 — Apr 19, 2026. Contains 2026-04-19 correction for target venue strategy. See that entry for details on what was corrected and why.*
