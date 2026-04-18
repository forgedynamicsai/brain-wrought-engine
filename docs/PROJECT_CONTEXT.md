# PROJECT_CONTEXT

**Project:** Brain-Wrought
**Owner:** Arron Street (independent; not affiliated with any commercial entity)
**Status:** Phase 1 — retrieval axis in active build
**Target v1 public:** Summer 2026
**Primary submission targets:** Arxiv preprint on v1 launch; NeurIPS 2027 Evaluations & Datasets Track as formal academic venue

---

## 1. What is Brain-Wrought

Brain-Wrought is an independent open benchmark for personal AI knowledge systems — "personal brains" in the Garry Tan / Obsidian / second-brain-agent sense. It evaluates AI systems that read, maintain, and reason over a personal knowledge vault across three axes:

- **A. Retrieval** — does the brain find what's already filed?
- **B. Ingestion** — can the agent turn raw inbox content into a well-structured brain?
- **C. Assistant / personalization** — does the agent actually know the user?

Each axis yields a score with bootstrap confidence intervals. A weighted composite ranks submissions on a public leaderboard. Qrels, gold graphs, and actual judge rubrics live in a sealed private repo; fixtures are randomized per submission.

## 2. Why it exists

### 2.1 Benchmark gap

No current benchmark covers the full personal-knowledge-agent loop:
- RAGAS measures RAG quality generally, not personal knowledge
- MTEB is embeddings
- HELMET is long-context
- LongMemEval is conversational memory
- GAIA is general assistant (and Berkeley showed it's exploitable)
- PrivacyBench is privacy in personal AI
- PersonaBench / LaMP is persona/personalization
- gbrain eval is retrieval-only

Meanwhile, a dozen personal-brain-agent systems (Mem0, Cognee, COG, Smart2Brain, Obsidian-second-brain skill, gbrain forks) ship without a shared evaluation standard.

### 2.2 Exploitability crisis

Berkeley RDI published (April 11, 2026) that an automated scanning agent hit near-perfect scores on 7 of 8 major agent benchmarks (SWE-bench Verified, SWE-bench Pro, Terminal-Bench, FieldWorkArena, CAR-bench at 100%; WebArena ~100%, GAIA 98%; OSWorld 73%) *without solving a single task*. Exploits included trojanizing test infrastructure, reading answer keys from config files, and prompt injection on LLM judges. Source: rdi.berkeley.edu, April 2026.

Brain-Wrought is designed from day one to resist these patterns:
- Sealed qrels (private repo, pulled at eval time via CI token)
- Fixture randomization (entity names, query order, adversarial injection rotation)
- Judge panel voting (3 models, majority vote, bootstrap CI)
- Rubric sealing (public rubric scaffold for submitters; actual rubrics sealed)
- Held-out test sets (public dev set for tuning, private test for scoring)

### 2.3 Opportunity window

- Berkeley RDI attention is peak (the April 2026 exploit paper landed one week before Phase 0 kickoff)
- Mem0, Cognee, COG, and the broader personal-brain-agent ecosystem have no shared evaluation standard
- Garry Tan's gbrain has retrieval eval but not full 3-axis framework
- Window to plant flag as the neutral third-party benchmark: ~60-90 days before a vendor (Mem0 or Cognee most likely) ships their own eval as marketing
- Each public axis release (retrieval → ingestion → assistant) is its own attention moment; staged public launches compound reach

## 3. Who Arron is

Arron is a U.S. Foreign Service civil servant, currently FPM at U.S. Consulate General Guangzhou. Background: Navy Electrical Repairman → San Diego Passport Agency → Consular Section Chief Libreville (Gabon) → current role. Academic: International Studies (University of Denver, Mandarin minor). PCS departure from Guangzhou September 2026.

Technical: ~10 years federal service, strong M365 (SharePoint, Power Automate, PowerBI), full-stack deployment experience (React/Node/Supabase/Stripe for WealthAgent), LangGraph + Pydantic v2 + LiteLLM (Forge Dynamics), Claude Code daily driver, GitHub `arronstreet-ops`. Brain-Wrought repos hosted under the `forgedynamicsai` GitHub org for operational convenience; no commercial attachment or revenue.

Portfolio posture: Brain-Wrought is a side project (8-10 hrs/week). WealthAgent in maintenance. Forge Dynamics paused. Career aim: GS-13+ domestic senior-level role in federal AI evaluation / assurance work — NIST AI Safety Institute, GSA/18F, DHS AI Corps, or similar — not a return to passport work.

## 4. Why not a business

Federal ethics rules (applicable to Foreign Service civil servants) prohibit outside-source income. Therefore:

- **No monetization infrastructure** in the build (no Stripe, no billing tables, no enterprise tier)
- **No commercial entity** attached to the benchmark (repos live in `forgedynamicsai` GitHub org purely for operational convenience; no Forge Dynamics commercial activity touches Brain-Wrought, and none is planned before PCS)
- **No prize-track target.** Initial planning incorrectly identified AgentX-AgentBeats Phase 2 as a benchmark-submission prize venue; it is not — Phase 2 is a competing-agent tournament, and the Phase 1 benchmark-submission window closed January 15, 2026. Prize money remains permissible in principle if a suitable venue appears, but the current plan does not depend on any prize.
- **Arxiv preprint** alongside v1 launch as the primary independent artifact
- **NeurIPS 2027 Evaluations & Datasets Track** as the formal academic venue (abstract deadline ~May 2027; conference Dec 2027). Brain-Wrought fits the ED track's explicit scope: "rigorous reproduction, auditing, and stress-testing of prior evaluations."
- Any future prize receipt (none currently foreseen) triggers annual financial disclosure (OGE-450 or OGE-278); cash prizes are clean, non-cash (advisory seats, equity, sponsor-funded travel) needs Post Ethics Counselor review before acceptance.

## 5. Strategic positioning

Brain-Wrought positions as the **neutral, independent, Berkeley-proof benchmark** for personal AI knowledge systems. The story:

- Independent — no commercial sponsor, no vendor alignment, no lock-in
- Reproducible — Docker, pinned versions, deterministic seeds, public CI from day one
- Exploit-resistant — designed against Berkeley's April 2026 findings
- Three-axis — covers what competitors miss (ingestion, personalization, roundtrip)
- Open source (harness, engine, skills) with sealed qrels

Developmental goal for Arron: credibility for GS-13+ transition into federal AI evaluation work. Not product, not revenue — a resume-strong public artifact with academic credibility, community impact, and demonstrable technical depth specifically in the benchmark-design subspecialty that federal AI evaluation teams actually hire for.

## 6. Related prior work

| Project | What it is | Relationship |
|---|---|---|
| gbrain (garrytan) | Personal brain system + retrieval eval harness | Brain-Wrought extends gbrain's retrieval eval pattern (P@k, Recall@k, MRR, nDCG@k) and adds 2 new axes. Plan is to DM Garry for collaboration/cross-link at Phase 1 public launch. |
| Mem0 | Agent memory framework; ~49% on LongMemEval | Target submitter. Invite for eval post-launch. |
| Cognee | Knowledge-graph agent memory | Target submitter. Invite for eval post-launch. |
| COG (huytieu) | Second brain with 17 AI skills, gbrain-inspired | Target submitter. |
| Obsidian-second-brain (eugeniughelbur) | Claude Code skill for Obsidian | Target submitter. |
| LongMemEval | Conversational memory eval | Adjacent, not competing. Cite in paper. |
| RAGAS | General RAG eval | Adjacent, not competing. Cite in paper. |
| PrivacyBench | Privacy in personalized AI | Adjacent; may integrate a subset as Axis C submodule. |
| Berkeley RDI exploit paper (Apr 2026) | Showed 7/8 benchmarks exploitable | Primary motivation; cite prominently; Brain-Wrought designed as response. |

## 7. Success criteria

**Minimum** (v0.5, approx. Week 2-3):
- Retrieval axis public
- Reference submission (naive grep baseline) runs end-to-end
- Public leaderboard live
- Blog post + X announcement

**Target** (v1.0, summer 2026):
- All three axes public
- 3+ reference submissions (naive, basic RAG, gbrain-style)
- Docker container for full reproduction
- Arxiv preprint posted (cs.IR + cs.LG + cs.AI)
- Public announcement thread; DMs to Garry Tan, Mem0, Cognee, Dawn Song
- HN Show post; r/LocalLLaMA and r/ObsidianMD cross-posts

**Stretch** (post-v1, through PCS in September 2026):
- 5+ external submissions on leaderboard within 30 days of v1
- Citation in a Mem0 or Cognee blog post
- Listed or discussed in Berkeley RDI's weekly newsletter
- v1.1 with community feedback incorporated

**Formal academic target** (Spring 2027):
- NeurIPS 2027 Evaluations & Datasets Track submission (abstract ~May 2027, conference Dec 2027)
- By submission time, v1 will have ~10-11 months of production use, community feedback, and any corrections baked into v1.x
