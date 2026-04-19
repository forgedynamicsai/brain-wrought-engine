BW-007: Synthetic inbox generator for Phase 2 (ingestion axis).

Repo: brain-wrought-engine
Branch: issue/BW-007-synthetic-inbox (create from current main)
Model: Sonnet 4.6 (you)
Estimated wall-clock: 3-4 hours

## Permission model

--dangerously-skip-permissions is assumed. Do not stop mid-task to
ask for approval. If architectural concerns surface that aren't
covered by this spec, STOP and report findings; do not patch around
them or proceed with uncertain changes.

## Context

Phase 2 of BrainWrought evaluates the INGESTION axis: can an agent
turn raw inbox content (emails, PDFs, meeting notes, Slack
transcripts) into a well-structured personal brain?

BW-007 creates the INPUT side of that evaluation: a deterministic
synthetic inbox generator that produces realistic multi-format
inbox content for seed-reproducible ingestion testing.

This is a fixture generator, not a scorer. It produces the raw
content that submission systems will ingest.

## Required output structure

The generator produces a directory of simulated inbox artifacts:

    inbox_<seed>/
    ├── emails/
    │   ├── 2026-04-03_re_product_launch.eml
    │   ├── 2026-04-05_meeting_notes_alpha.eml
    │   └── ... (20-40 emails)
    ├── documents/
    │   ├── Q1_budget.xlsx       (generated as CSV for simplicity,
    │   │                         rename to .xlsx-compatible with openpyxl)
    │   ├── project_alpha_spec.pdf
    │   └── ... (5-15 documents)
    ├── calendar/
    │   └── events.ics            (iCalendar format, 30-50 events)
    ├── slack/
    │   └── threads.json          (Slack export-style JSON, 10-30 threads)
    └── metadata.json             (inventory of all generated artifacts
                                   with types, dates, and associated entities)

## Acceptance criteria

- [ ] `python -m brain_wrought_engine.fixtures.inbox.generate
       --count 1 --seed 42 --out /tmp/test_inbox/` produces one
      inbox directory named `inbox_42/`
- [ ] Each inbox contains: 20-40 emails, 5-15 documents, 30-50
      calendar events, 10-30 Slack threads
- [ ] All content references the SAME entity pool as
      brain_wrought_engine.fixtures.generator (the 200 synthetic
      people / 50 companies / 30 projects). Import the entity
      constants from that module; do NOT define a new pool.
- [ ] Generation is fully deterministic: same seed → bit-identical
      output including filenames, timestamps inside emails, message
      ordering
- [ ] Uses Haiku 4.5 batch API via LiteLLM for natural language
      content (email bodies, Slack messages, calendar event
      descriptions). Cost cap: $2 per 100-inbox generation run.
      If you can't guarantee this, use templated content instead
      and document the tradeoff.
- [ ] `metadata.json` enumerates every artifact with:
      {filename, type, timestamp, mentioned_entities[]}
- [ ] Unit tests for determinism (same seed → identical output)
- [ ] Unit tests for entity consistency (every mentioned_entity is
      in the canonical entity pool)
- [ ] Integration test: generate one inbox, validate structure

## Technical notes

- Email format: RFC 5322 .eml files, with From/To/Subject/Date
  headers and plain-text body
- PDF: use reportlab to generate simple multi-page PDFs (title,
  executive summary, body). Don't over-engineer layout.
- xlsx: openpyxl with 2-3 sheets of synthetic numeric data and
  some named ranges
- ics: icalendar library (pip install icalendar)
- Slack JSON: mimic Slack export schema {channel, thread_ts,
  messages: [{user, ts, text}]}
- Seed propagation: derive sub-seeds from parent seed for each
  content category (emails get seed+1, docs get seed+2, etc.)
  so changing one category's generator doesn't affect others
- Timestamps: anchored to a fixed reference date (2026-04-01)
  to prevent temporal drift across runs
- Entity mentions: use wikilink-style [[Alice Hartman]] where
  natural (in Slack messages, some email bodies), plain-text
  elsewhere (emails to external parties would not use wikilinks)

## Files to create

- brain_wrought_engine/fixtures/inbox/__init__.py
- brain_wrought_engine/fixtures/inbox/generate.py (main entrypoint)
- brain_wrought_engine/fixtures/inbox/emails.py
- brain_wrought_engine/fixtures/inbox/documents.py
- brain_wrought_engine/fixtures/inbox/calendar.py
- brain_wrought_engine/fixtures/inbox/slack.py
- brain_wrought_engine/fixtures/inbox/metadata.py
- tests/fixtures/inbox/test_determinism.py
- tests/fixtures/inbox/test_entity_consistency.py
- tests/fixtures/inbox/test_integration.py

## Out of scope

- Do NOT create the gold entity graph. That's BW-008 running in
  parallel — it will consume your metadata.json output.
- Do NOT score anything. This is fixture generation only.
- Do NOT modify brain_wrought_engine/fixtures/generator.py (the
  clean-schema vault generator). It's working and stable.
- Do NOT add email-parsing infrastructure — just generation.

## Dependencies to add

Via poetry add (pinned, no carets per CLAUDE.md):

    reportlab = "4.2.5"
    openpyxl = "3.1.5"
    icalendar = "6.1.0"

Verify compatibility with pyyaml 6.0.3 and numpy 2.2.1 already
pinned. If any conflict, STOP and report.

## Deliverable

Open PR titled "[BW-007] Synthetic inbox generator" against main.
Report:
- Commit SHA
- Test count (existing + new)
- Sample inbox size (bytes + file counts)
- Actual Haiku API cost for generating 3 test inboxes
- Any architectural concerns

STOP conditions (report, don't fix):
- If Haiku cost per inbox exceeds $1
- If deterministic reproducibility can't be verified (seed same
  twice → different output)
- If the entity pool import from fixtures.generator can't be
  cleanly reused
