# RISKS

Risk register. Sorted by severity × likelihood. Update when new risks surface or existing ones change.

Severity: 1 (nuisance) to 5 (project-killing).
Likelihood: 1 (unlikely) to 5 (near-certain).

---

## R-01: Competitor ships personal-brain eval first

- **Severity:** 4 — significant erosion of novelty claim
- **Likelihood:** 4 (up from 3 in v1 — without AgentX as a forcing function, Brain-Wrought's timeline is driven primarily by competitor preemption)
- **Description:** Mem0, Cognee, or a Berkeley-aligned team ships a personal-brain benchmark before v1.0
- **Signals:** Mem0 or Cognee blog posts on eval methodology; Berkeley RDI weekly newsletter; new arxiv papers tagged cs.IR + personalization
- **Mitigation:** Ship retrieval axis publicly in early May. Planting flag publicly at Phase 1 means later entrants become "alternative to Brain-Wrought" rather than "first in category". Each axis release is its own attention moment.
- **Contingency:** If a direct competitor appears, pivot positioning to "Brain-Wrought is the axis-complete, sealed-qrels alternative" — emphasizing specific differentiators (three axes, Berkeley-exploit-resistance, reproducibility discipline)
- **Owner:** Arron

## R-02: Sealed qrels leak

- **Severity:** 5 — benchmark integrity collapses
- **Likelihood:** 2
- **Description:** Private repo gets forked, leaked via GitHub Actions logs, or accidentally made public
- **Signals:** Sudden jump in submission scores; external party citing specific qrel content
- **Mitigation:** 2FA on GitHub account; branch protection on sealed repo; minimal CI token scope; rotate qrels every 6 months; adversarial injection suite rotates every 30 days
- **Contingency:** `/SECURITY.md` documents response: rotate all content, flag affected submissions, publicly disclose in blog post
- **Owner:** Arron

## R-03: PCS disruption (September 2026)

- **Severity:** 3 — if v1 ships on time, PCS is not a blocker
- **Likelihood:** 5
- **Description:** Physical move from Guangzhou to continental US disrupts 4-6 weeks of work
- **Mitigation:** v1 ships summer 2026 — 2+ months before PCS. Arxiv preprint can be finalized in July. If v1.x maintenance is mid-PCS, defer to November.
- **Contingency:** Post-v1 work is optional; no hard deadlines after July until NeurIPS 2027 submission in May 2027
- **Owner:** Arron

## R-04: Foreign Service ethics / OPM guidance concern

- **Severity:** 4 — could require pausing or restructuring
- **Likelihood:** 2
- **Description:** Post Ethics Counselor identifies conflict with outside-activity rules (3 FAM 4120). Primary flag point: repos hosted under `forgedynamicsai` GitHub org despite Forge Dynamics being a pre-revenue commercial entity.
- **Mitigation:** Brain-Wrought has no commercial attachment, no revenue, no marketing, no licensing. Repos-under-Forge-Dynamics-org is operational convenience, not commercial integration. Confirm with Post Ethics Counselor before public launch (target: before Phase 1 blog post); document clearance in DECISIONS.md.
- **Contingency:** If issues raised: pause public launch, transfer repos to a standalone `brain-wrought` GitHub org, resume. GitHub redirects preserve clone URLs and early stars/watchers.
- **Owner:** Arron
- **Action:** Schedule Ethics Counselor check-in by end of April (before Phase 1 public launch)

## R-05: Judge panel cost explosion

- **Severity:** 2
- **Likelihood:** 2
- **Description:** Per-submission eval cost creeps above $10 due to prompt growth, judge count, or model pricing changes
- **Mitigation:** Aggressive caching on rubrics (cached input is 10% of standard rate). Cap panel at 3 judges. Monitor per-submission cost weekly.
- **Contingency:** If cost > $10/submission: reduce to 2 judges + Cohen kappa, flag as v1 limitation, fix in v1.1
- **Owner:** Arron

## R-06: Judge inter-rater agreement low

- **Severity:** 3 — undermines axis C credibility
- **Likelihood:** 2
- **Description:** Fleiss kappa across 3 judges on pilot set < 0.4 — judges aren't agreeing, score noise dominates
- **Signals:** High CI width in pilot bootstrap; > 20% of samples flagged as "contested" (SD > 1.5)
- **Mitigation:** Red-team rubrics before sealing; use 3 + 3 few-shot exemplars per rubric; pilot with 20 tasks before committing
- **Contingency:** Rewrite rubrics; if persistent, add 2 more judges (5-panel); ultimately, human-audit subset
- **Owner:** Arron

## R-07: Prompt injection succeeds against judges

- **Severity:** 4 — exploits are headline news; Brain-Wrought becomes case study of its own failure
- **Likelihood:** 3
- **Description:** Submission successfully injects instructions that trick judges into high scores
- **Mitigation:** Adversarial injection suite tested during rubric design. Panel voting catches single-judge injection. Rubric rotation on 90-day cadence.
- **Contingency:** Delist affected submissions, add the successful injection to adversarial suite, publicly disclose
- **Owner:** Arron

## R-08: Garry Tan or Berkeley RDI builds competing/supervening framework

- **Severity:** 3
- **Likelihood:** 3
- **Description:** Garry Tan extends gbrain eval to full 3-axis; Berkeley RDI publishes their own personal-brain benchmark design
- **Mitigation:** DM Garry Tan at Phase 1 public launch offering collaboration/cross-linking; frame Brain-Wrought as complement to gbrain, not replacement
- **Contingency:** If Garry builds parallel: propose integration/alliance; if Berkeley supersedes: focus Brain-Wrought on axis B (ingestion — still unique), submit as complementary work
- **Owner:** Arron

## R-09: Arron burnout / overcommitment

- **Severity:** 4 — Brain-Wrought collapses if Arron can't sustain
- **Likelihood:** 3
- **Description:** 8-10 hrs/week side project + FPM job + PCS prep + remaining content tracks + family. Real risk of capacity breach.
- **Signals:** Missed Wave deadlines by > 1 week; commit frequency drops; DECISIONS.md stops updating
- **Mitigation:** Forge Dynamics paused (capacity reclaimed). Content cadence reduced to 10-14 days. WealthAgent pure maintenance.
- **Contingency:** If slipping, cut scope to retrieval-only v1 and ship that as the arxiv preprint. Better than nothing.
- **Owner:** Arron

## R-10: Reproducibility audit fails on a top-5 submission

- **Severity:** 3
- **Likelihood:** 2
- **Description:** Top submitter's scores can't be reproduced in manual audit; accusations of inconsistent enforcement
- **Mitigation:** Reproducibility spec is precise and published. CI continuously validates reference submissions.
- **Contingency:** Delist with public explanation. Appeals process (SUBMISSION_PROTOCOL.md §10) available to submitter.
- **Owner:** Arron

## R-11: Anthropic or OpenAI deprecates a judge model mid-cycle

- **Severity:** 2
- **Likelihood:** 3
- **Description:** Sonnet 4.6, Opus 4.7, or GPT-5.4 deprecated before v1.5
- **Mitigation:** Snapshot IDs pinned where providers expose them; fallback judges identified (Gemini 3.1 Pro for GPT-5.4 slot)
- **Contingency:** Release v1.x with migrated judges; re-baseline reference submissions; clearly mark leaderboard transition
- **Owner:** Arron

## R-12: Supabase/Vercel/Railway service interruption

- **Severity:** 2
- **Likelihood:** 2
- **Description:** Leaderboard unavailable; submission intake fails
- **Mitigation:** GitHub Actions-based eval doesn't depend on these (runs on GitHub infra). Leaderboard page can be static-generated from GitHub data.
- **Contingency:** Static export of leaderboard hosted on GitHub Pages as fallback
- **Owner:** Arron

## R-13: Astrill VPN disruption

- **Severity:** 2
- **Likelihood:** 3
- **Description:** Arron's Chinese-domicile VPN becomes unreliable, blocking access to Claude, GitHub, etc.
- **Mitigation:** VPN has worked consistently in past projects. Maintain backup (secondary VPN provider) ready to activate.
- **Contingency:** Use mobile hotspot via international SIM if needed
- **Owner:** Arron

## R-14: Novelty claim disputed

- **Severity:** 3
- **Likelihood:** 3
- **Description:** Arxiv readers or NeurIPS 2027 reviewers identify a prior benchmark that substantially covers the same territory
- **Mitigation:** Thorough related-work scan before v1 launch (covered in PROJECT_CONTEXT §6). Arxiv paper transparent about what's novel vs. extended.
- **Contingency:** If substantial overlap identified: amend positioning ("Brain-Wrought extends X by adding Y and Z"). Novelty is rarely binary.
- **Owner:** Arron

## R-15: Target venue drift / academic momentum decay (new in v2)

- **Severity:** 2
- **Likelihood:** 2
- **Description:** NeurIPS 2027 submission is ~10 months post-v1. Without a near-term forcing function (like a prize deadline), the project could drift into maintenance and lose academic-submission momentum.
- **Signals:** v1.x updates stop; no engagement with external submitters; Arron's attention pulled to post-PCS career tasks
- **Mitigation:** Calendar the NeurIPS 2027 ED abstract deadline in Arron's core planning tool; schedule a "preprint → paper" conversion milestone for early 2027; treat NeurIPS submission as a first-class deliverable, not an afterthought
- **Contingency:** If NeurIPS 2027 is missed, alternate venues: ICLR 2028 (deadline ~Sept 2027), CHI 2027 if positioning shifts toward HCI, or KDD 2027 Datasets & Benchmarks track (dual cycles per year)
- **Owner:** Arron

---

*(Add new risks below as they surface. Review weekly.)*

---

*v2 — Apr 19, 2026. Changes from v1:*
- *R-01 likelihood increased from 3 to 4 (no AgentX forcing function means timeline hinges primarily on competitor preemption)*
- *R-03 contingency timeline updated to reference NeurIPS 2027 rather than AgentX Phase 2*
- *R-04 mitigation expanded to address the forgedynamicsai org hosting decision*
- *R-09 contingency updated — retrieval-only v1 goes to arxiv, not AgentX*
- *R-14 reframed — reviewers are arxiv + NeurIPS, not AgentX*
- *R-15 added — academic momentum decay over the 10-month gap between v1 and NeurIPS 2027*
