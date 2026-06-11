#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

DEFAULT_TOKEN_PATTERN = r"_readout_phase[^_]+"
DEFAULT_NAME_FILTER = "readout_phase_2"

def shortened_name(name: str, token_pattern: re.Pattern[str]) -> str:
    return token_pattern.sub("", name, count=1)


def gather_candidates(
    root: Path,
    *,
    name_filter: str,
    token_pattern: re.Pattern[str],
) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    dirs: list[Path] = []
    for path in root.rglob("*"):
        if name_filter not in path.name:
            continue
        new_name = shortened_name(path.name, token_pattern)
        if new_name == path.name:
            continue
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            dirs.append(path)
    dirs.sort(key=lambda p: len(p.parts), reverse=True)
    return files, dirs


def validate_plan(
    paths: list[Path],
    *,
    token_pattern: re.Pattern[str],
) -> list[tuple[Path, Path]]:
    plan: list[tuple[Path, Path]] = []
    seen_targets: set[Path] = set()
    for src in paths:
        dst = src.with_name(shortened_name(src.name, token_pattern))
        if dst in seen_targets:
            raise FileExistsError(f"Collision in planned targets: {dst}")
        if dst.exists() and dst != src:
            raise FileExistsError(f"Target already exists: {dst}")
        seen_targets.add(dst)
        plan.append((src, dst))
    return plan


def run_plan(plan: list[tuple[Path, Path]], apply: bool) -> int:
    if not plan:
        print("No matching paths found.")
        return 0

    print(f"Planned renames: {len(plan)}")
    for src, dst in plan:
        print(f"{src} -> {dst}")

    if not apply:
        print("\nDry run only. Re-run with --apply to execute.")
        return 0

    for src, dst in plan:
        src.rename(dst)
    print("\nRenaming complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Shorten sweep names by removing '_number_measurements...'"
            " from files and directories."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute renaming. Without this flag, only prints planned changes.",
    )
    parser.add_argument(
        "--token-pattern",
        default=DEFAULT_TOKEN_PATTERN,
        help=(
            "Regex pattern removed once from each matching name "
            f"(default: {DEFAULT_TOKEN_PATTERN!r})."
        ),
    )
    parser.add_argument(
        "--name-filter",
        default=DEFAULT_NAME_FILTER,
        help=(
            "Only paths whose filename contains this string are considered "
            f"(default: {DEFAULT_NAME_FILTER!r})."
        ),
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root does not exist: {root}")
        return 1

    try:
        token_pattern = re.compile(args.token_pattern)
    except re.error as exc:
        print(f"Invalid --token-pattern regex: {exc}")
        return 3

    files, dirs = gather_candidates(
        root,
        name_filter=args.name_filter,
        token_pattern=token_pattern,
    )
    try:
        file_plan = validate_plan(files, token_pattern=token_pattern)
        dir_plan = validate_plan(dirs, token_pattern=token_pattern)
    except FileExistsError as exc:
        print(f"Error: {exc}")
        return 2

    full_plan = file_plan + dir_plan
    return run_plan(full_plan, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
