# BUILD_PLAN — Warpspeed

**Start:** Apr 18, 2026 (Phase 0 complete)
**v1 Public Target:** Summer 2026 (approximately Jun-Jul 2026)
**Pace:** 8-10 hrs/week, public milestone every 2-3 weeks
**Why warpspeed without AgentX:** Berkeley exploit paper attention window (peak Apr-Jul 2026); competitor preemption (Mem0/Cognee likely to ship their own evals in 60-90 days); PCS in September 2026 creates a natural end-of-summer deadline for active build

---

## Phase 0 — Architecture + Scaffolding (Apr 18-20) ✓

Complete. Four repos scaffolded under `forgedynamicsai` GitHub org, ADRs committed, CI skeletons in place, Agent Orchestrator configured, Wave 1 issues opened.

---

## Phase 1 — Retrieval Axis Public (Apr 21 - early May) — IN PROGRESS

**Weeks 1-2.** Ship retrieval first. Fastest credible public artifact.

**Wave 1 status:**
- `[BW-001]` Clean-schema fixture generator ✓ merged
- `[BW-003]` P@k, Recall@k, MRR, nDCG@k scorers ✓ merged
- `[BW-005]` Supabase `brain_wrought` schema with RLS ✓ merged

**Wave 2 status:**
- `[BW-002a]` Qrel data models + wikilink expansion skeleton ✓ merged
- `[BW-004a]` Evaluate CLI command skeleton ✓ merged

**Wave 2b (active):**
- `[BW-002b]` Typed queries (factual/temporal/personalization/abstention), non-title query text, LiteLLM Sonnet verification
- `[BW-004b]` Rename evaluate→self-eval, add submit stub, wire Docker subprocess, YAML config loading

**Round 3:**
- `[BW-006]` Reference submission: naive grep baseline — blocked on BW-002b AND BW-004b merging

**Go/no-go gate:** Reference submission scores end-to-end on public dev set with real typed qrels. Leaderboard page deployed (even if empty).

**Public milestone (early May):**
- Blog post: "Brain-Wrought v0.5: Measuring personal brain retrieval"
- X thread from @vitelloma
- Post to r/LocalLLaMA, r/ObsidianMD, HN
- DM Garry Tan with preview + collaboration offer

---

## Phase 2 — Ingestion Axis Public (mid-May — early June)

**Weeks 3-5.** The hard axis. The one nobody measures.

**Wave 2 issues:**
- `[BW-007]` Synthetic inbox generator (emails, PDFs, xlsx, calendar, Slack sim)
- `[BW-008]` Gold entity graph generator (seeded, deterministic)
- `[BW-009]` Entity recall scorer
- `[BW-010]` Backlink F1 scorer (vs gold graph)
- `[BW-011]` Citation accuracy scorer
- `[BW-012]` Schema completeness rubric scorer
- `[BW-013]` Setup friction scorer (counts commands + prompts required)
- `[BW-014]` Dirty-schema fixture generator (50 brains with stubs, missing fields, stale dates)

**Go/no-go gate:** Reference submission scores on both clean + dirty fixture tiers.

**Public milestone (late May / early June):**
- Blog post: "The ingestion axis — the one nobody measures"
- X thread
- Update leaderboard with axis B scores for all submissions

---

## Phase 3 — Assistant Axis + v1 Prep (early — mid June)

**Weeks 6-8.** Port Forge Dynamics judge panel. Seal rubrics. Bootstrap confidence intervals.

**Wave 3 issues:**
- `[BW-015]` Judge panel subgraph (LangGraph port from Forge Dynamics)
- `[BW-016]` Judge adapter (LiteLLM → Sonnet 4.6 + Opus 4.7 + GPT-5.4)
- `[BW-017]` Rubric loader (pulls sealed rubrics from CI at eval time)
- `[BW-018]` Bootstrap confidence interval module
- `[BW-019]` Identity accuracy rubric (sealed)
- `[BW-020]` Stance coherence rubric (sealed)
- `[BW-021]` Novelty vs regurgitation rubric (sealed)
- `[BW-022]` Calibration rubric (sealed)
- `[BW-023]` Red-team judges against prompt injection (adversarial suite v1)
- `[BW-024]` Morning-brief / meeting-prep / synthesis task fixtures (70 tasks)

**Go/no-go gate:** Judge panel inter-rater agreement > 0.6 Fleiss kappa on pilot subset. Injection suite passes (judges don't score injected submissions highly).

---

## Phase 4 — v1.0 Launch (late June — mid July)

**Week 9 target window.** Ship, publish, announce.

**v1.0 release:**
- v1.0 git tag + signed release
- Docker image pushed to GHCR (tagged + signed)
- Full reproducibility run from fresh clone → matching scores
- All three axes public and scored
- 3+ reference submissions published with baseline scores

**Arxiv preprint (cs.IR primary; cs.LG + cs.AI cross-listed):**
- Technical write-up framing Brain-Wrought as a response to the Berkeley April 2026 exploit paper
- Describes the three-axis framework, sealed-artifacts pattern, judge panel design, reproducibility guarantees
- Presents baseline results across reference submissions
- Discusses known limitations honestly
- Submitted the same day as v1.0 tag

**Public launch campaign:**
- Launch thread on X from @vitelloma
- HN Show post
- r/LocalLLaMA, r/ObsidianMD, r/MachineLearning cross-posts
- DMs to: Garry Tan, Mem0 team, Cognee team, Dawn Song (Berkeley RDI)
- Email Berkeley RDI weekly newsletter with preprint link

**Stretch goals for the launch week:**
- Apply for HuggingFace leaderboard listing
- Contact PrivacyBench authors about a submodule integration for v1.1
- Invite 3-5 target submitters to run their systems privately before public submission

---

## Phase 5 — NeurIPS 2027 ED Track submission (Spring 2027, post-PCS)

This phase is the formal academic capstone, occurring ~10 months after v1.0 ships. By submission time, Brain-Wrought will have:

- Been used by external teams (ideally 10+ submissions on the leaderboard)
- Had v1.1 or v1.2 with community feedback incorporated
- Accumulated citations in blog posts, other papers, or vendor material
- Demonstrated reproducibility holds in practice (CI history as evidence)

**NeurIPS 2027 Evaluations & Datasets Track** — abstract deadline approximately May 2027, full paper ~1 week later, conference Dec 2027. The track explicitly welcomes "rigorous reproduction, auditing, and stress-testing of prior evaluations" and "benchmark saturation or overfitting and their impact on scientific conclusions." Brain-Wrought fits exactly.

The paper at this stage is meaningfully different from the arxiv preprint: it reflects production use, includes external submission analyses, and presents findings about the personal-brain-agent ecosystem that only become visible after months of leaderboard activity.

---

## Compression mechanics

How warpspeed actually works:

| Lever | Savings |
|---|---|
| Parallel agents via Agent Orchestrator v0.1.0 (Arron's WealthAgent pattern) | ~40% schedule compression on implementation |
| Haiku 4.5 batch for all fixture generation | 50x cost savings, 5x time savings vs. Opus |
| Aggressive prompt caching (90% off on cached input) | ~50% cost savings on repeated system prompts |
| Skill reuse from existing arsenal (see SKILL_REUSE_MAP.md) | ~40-50% build work eliminated |
| Ship per axis instead of big-bang v1 | 3 public moments instead of 1 |
| ADR-driven, no architecture relitigation | Zero scope creep from revisits |
| Split PRs where agents under-scope (see BW-002 a/b and BW-004 a/b pattern) | Preserves correct scaffolding while being honest about what's complete |

## Risk-adjusted contingencies

If any phase slips by > 1 week:

- **Slip in Phase 1:** Ship retrieval with fewer queries (minimum 100 total, 50 public / 50 sealed). Never ship without sealed test set.
- **Slip in Phase 2:** Drop "setup friction" scorer to Phase 3. It's the least-essential ingestion sub-metric.
- **Slip in Phase 3:** Ship with 2 judges instead of 3; Fleiss kappa → Cohen kappa. Flag as v1.0 limitation; fix in v1.1.
- **Slip in Phase 4:** Arxiv preprint can follow v1 launch by 1-2 weeks. Don't delay launch for preprint polish.

**Never compromise:**
- Sealed qrels (ship with nothing else before they exist)
- Deterministic seeds (reproducibility is the whole claim)
- Reference submission that runs end-to-end (without this there's no leaderboard)

## Weekly rhythm

- Mon/Tue evening: Claude Code build sessions, Agent Orchestrator waves
- Wed: ADR review, blocker unstick, red-team whatever's new
- Thu/Fri: light; catch up on breaking research (arxiv, X from Berkeley RDI, Mem0/Cognee)
- Sat: public-milestone push if week ends on a public milestone
- Sun: plan next week, update DECISIONS.md, RISKS.md

## North star

Every commit should increase the probability that Brain-Wrought is cited as *the* neutral personal-brain benchmark when Mem0, Cognee, or Berkeley RDI references this space. Every feature should serve credibility, reproducibility, or resistance to exploitation. Anything else is scope creep.
