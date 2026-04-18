"""CLI entry point for the brain vault fixture generator.

Usage
-----
python -m brain_wrought_engine.fixtures generate \\
    --count 3 --seed 42 --out /tmp/bw-test [--no-llm]

Subcommands
-----------
generate  Generate *count* brain vaults.
validate  Validate an existing vault directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from brain_wrought_engine.fixtures.generator import generate_brain
from brain_wrought_engine.fixtures.validator import validate_brain


def _cmd_generate(args: argparse.Namespace) -> int:
    out = Path(args.out)
    for i in range(args.count):
        vault = generate_brain(
            seed=args.seed,
            fixture_index=i,
            out_dir=out,
            note_count=args.notes,
            use_llm=not args.no_llm,
        )
        print(f"[{i + 1}/{args.count}] generated: {vault}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_brain(Path(args.vault))
    if not errors:
        print("OK — vault is valid")
        return 0
    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m brain_wrought_engine.fixtures",
        description="Brain-Wrought fixture generator and validator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate sub-command
    gen = sub.add_parser("generate", help="Generate synthetic brain vaults")
    gen.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of vaults to generate (default: 1)",
    )
    gen.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Master random seed (default: 0)",
    )
    gen.add_argument(
        "--out",
        required=True,
        metavar="DIR",
        help="Parent directory for generated vaults",
    )
    gen.add_argument(
        "--notes",
        type=int,
        default=100,
        metavar="N",
        help="Notes per vault (default: 100)",
    )
    gen.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM body generation; use deterministic templates",
    )

    # validate sub-command
    val = sub.add_parser("validate", help="Validate an existing brain vault")
    val.add_argument("vault", metavar="DIR", help="Path to the vault directory")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return _cmd_generate(args)
    if args.command == "validate":
        return _cmd_validate(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
