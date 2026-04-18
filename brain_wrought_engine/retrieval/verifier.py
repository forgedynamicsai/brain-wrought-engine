"""LiteLLM-based verification pass for generated qrels."""

from __future__ import annotations

import json
import sys
from typing import Any

from litellm import completion

from brain_wrought_engine.retrieval.models import QrelEntry, QrelSet

_SYSTEM_PROMPT = (
    "You are a relevance judge for a personal knowledge system benchmark. "
    "Given a vault summary and a query, identify which note IDs are relevant. "
    'Respond with a JSON object: {"relevant_ids": ["id1", "id2"], "answerable": true/false} '
    "Only include note IDs that directly answer the query. "
    "If the query cannot be answered from the vault, "
    'return {"relevant_ids": [], "answerable": false}.'
)

_MAX_RETRIES = 3


def _build_user_message(entry: QrelEntry, vault_summary: dict[str, str]) -> str:
    """Build the user-turn message for a single qrel verification call."""
    vault_lines = "\n".join(
        f"  - {note_id}: {snippet}" for note_id, snippet in sorted(vault_summary.items())
    )
    return (
        f"Vault notes:\n{vault_lines}\n\n"
        f"Query: {entry.query_text}\n\n"
        "Which note IDs (if any) directly answer this query?"
    )


def _parse_llm_response(raw: Any) -> tuple[frozenset[str], bool]:
    """Parse the LiteLLM completion response into (relevant_ids, answerable).

    Raises ValueError if the response cannot be parsed.
    """
    try:
        content: str = raw.choices[0].message.content or ""
        data: dict[str, Any] = json.loads(content)
        relevant_ids: frozenset[str] = frozenset(data.get("relevant_ids", []))
        answerable: bool = bool(data.get("answerable", False))
        return relevant_ids, answerable
    except (AttributeError, IndexError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"Could not parse LLM response: {exc}") from exc


def verify_qrel(
    entry: QrelEntry,
    vault_summary: dict[str, str],  # {note_id: first_100_chars_of_content}
    *,
    base_seed: int,
) -> tuple[bool, QrelEntry | None]:
    """Verify a single qrel entry against vault content via LiteLLM.

    For non-abstention queries: asks the model which note IDs answer the query,
    then checks for set equality with entry.relevant_note_ids.

    For abstention queries: asks the model if the vault can answer the query,
    then checks that the model says it is NOT answerable.

    Retries up to 3 times (using base_seed + retry_index as the LiteLLM seed).
    After 3 consecutive failures, logs the entry details to stderr and returns
    (False, None).

    Parameters
    ----------
    entry:
        The qrel entry to verify.
    vault_summary:
        A mapping from note_id to the first ~100 characters of note content,
        used as the vault context passed to the LLM.
    base_seed:
        Base integer seed; each retry uses base_seed + retry_index so that
        retries are deterministic but distinct.

    Returns
    -------
    (True, entry)  — entry is valid (or corrected to match LLM judgment).
    (False, None)  — all retries exhausted; entry logged to stderr.
    """
    user_message = _build_user_message(entry, vault_summary)

    for retry_index in range(_MAX_RETRIES):
        try:
            response = completion(
                model="claude-sonnet-4-6",
                temperature=0.1,
                max_tokens=512,
                seed=base_seed + retry_index,
                messages=[
                    {
                        "role": "system",
                        "content": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
            )
            returned_ids, answerable = _parse_llm_response(response)
        except Exception as exc:
            # Log parse/network failures and retry
            print(
                f"[verifier] retry {retry_index}/{_MAX_RETRIES - 1} "
                f"error for {entry.query_id!r}: {exc}",
                file=sys.stderr,
            )
            continue

        if entry.query_type == "abstention":
            if not answerable:
                return True, entry
        else:
            if returned_ids == entry.relevant_note_ids:
                return True, entry

        print(
            f"[verifier] retry {retry_index}/{_MAX_RETRIES - 1} "
            f"mismatch for {entry.query_id!r}: "
            f"returned_ids={returned_ids!r}, "
            f"expected={entry.relevant_note_ids!r}, "
            f"answerable={answerable!r}",
            file=sys.stderr,
        )

    # All retries exhausted
    print(
        f"[verifier] FAILED after {_MAX_RETRIES} retries for entry:\n"
        f"  query_id={entry.query_id!r}\n"
        f"  query_text={entry.query_text!r}\n"
        f"  query_type={entry.query_type!r}\n"
        f"  relevant_note_ids={entry.relevant_note_ids!r}\n"
        f"  expected_abstain={entry.expected_abstain!r}",
        file=sys.stderr,
    )
    return False, None


def verify_qrel_set(
    qrel_set: QrelSet,
    vault_summary: dict[str, str],
    *,
    base_seed: int,
) -> tuple[int, int]:
    """Run verify_qrel over every entry in a QrelSet.

    Parameters
    ----------
    qrel_set:
        The full set of qrels to verify.
    vault_summary:
        Mapping from note_id to first ~100 chars of note content.
    base_seed:
        Passed through to verify_qrel; each entry uses base_seed + entry_index
        to keep verification seeds distinct across entries.

    Returns
    -------
    (n_valid, n_invalid)
        Counts of entries that passed and failed verification.
    """
    n_valid = 0
    n_invalid = 0
    for idx, entry in enumerate(qrel_set.entries):
        valid, _ = verify_qrel(entry, vault_summary, base_seed=base_seed + idx * _MAX_RETRIES)
        if valid:
            n_valid += 1
        else:
            n_invalid += 1
    return n_valid, n_invalid
