Fix BW-002c: qrel_generator produces unusable queries due to 
incorrect entity extraction and arbitrary relevance assignment.

Repo: brain-wrought-engine
Branch: issue/BW-002c-qrel-quality-fix
Model: Sonnet 4.6
Estimated: 3-5 hours

Full context in issue #16. Summary:
- Queries contain markdown structural text ("Overview\n", 
  "Background\n", "Key People") instead of actual entities
- relevant_note_ids don't actually map to notes that answer queries
- Entity extraction reads note body text instead of frontmatter 
  entities: field

BEFORE YOU CODE: read brain_wrought_engine/retrieval/qrel_generator.py 
fully. Understand the current entity extraction logic (which is 
broken). Understand the current relevance assignment (which is 
arbitrary). Do not modify the public API signature of generate_qrels 
— downstream code depends on it.

REQUIRED CHANGES:

1. Entity extraction uses frontmatter only.
   Parse each note's YAML frontmatter using pyyaml.
   Extract the entities: list (if present).
   Collect the union across all notes as the entity pool.
   If a note has no entities: field, it contributes no entities.
   Do NOT extract from note body, section headers, or titles.

2. Relevance definition (explicit and testable):
   A note N is relevant to a query Q about entity E iff:
   - E appears in N's frontmatter entities: list, OR
   - E appears as a [[wikilink]] target in N's body
   
   Document this in a docstring and in an ADR amendment to 
   ADR-001 (if relevant) or a new ADR if needed.

3. Query templates only reference entities known to be in the pool.
   Before filling a template, verify the chosen entity exists in 
   the extracted entity pool. If no entities are available (empty 
   vault or all notes lack frontmatter entities), raise ValueError 
   with a clear message — do NOT silently generate broken queries.

4. No newlines or markdown tokens in query text.
   After template fill, validate: no '\n', '\t', or lines starting 
   with '#' characters in query_text. Raise ValueError if violated.

NEW TESTS REQUIRED:

- test_no_newlines_in_queries: iterate all generated queries, 
  assert no query_text contains '\n'
- test_no_heading_tokens_in_queries: assert no query_text contains 
  literal 'Overview', 'Background', 'Notes', 'Connections' (the 
  standard section headings from generator.py templates)
- test_relevance_invariant: for every qrel entry, for each 
  relevant_note_id, load that note, verify the query's referenced 
  entity appears in the note's frontmatter entities OR body 
  wikilinks. Fails if a qrel cites a note that doesn't actually 
  contain the referenced entity.
- test_abstention_correctness: verify expected_abstain=True 
  qrels have empty relevant_note_ids AND query references an 
  entity NOT in the vault's entity pool

REGRESSION CHECK:

Use the existing test vault from generate_brain(seed=42, 
fixture_index=0, note_count=50, use_llm=False). Generate 20 qrels. 
Verify the test suite catches the old bugs: the tests above should 
FAIL against the current broken qrel_generator.py and PASS against 
the fixed version.

Confirm by checking out main briefly, running the new tests, 
observing failures, checking back out to the fix branch, 
observing passes. Document in PR description.

OUT OF SCOPE:

- LLM-based entity extraction (use frontmatter only)
- Fuzzy entity matching (exact string equality)  
- Cross-note entity resolution
- Any changes to generator.py (the vault generator is correct; 
  the bug is in qrel_generator.py)

DELIVERABLE:

Open a PR titled "[BW-002c] Fix qrel generator entity extraction 
and relevance definition" and stop. Do not merge. Report:
- Commit SHA
- Test count (new + old)
- Confirmation that new tests FAIL against main, PASS against fix
- Any architectural concerns surfaced during the work
