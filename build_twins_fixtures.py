#!/usr/bin/env python3
"""
build_twins_fixtures.py v0.3 -- twin-paradigm fixture builder (split edition).

Engine file; positions live in twins_data.py. Writes twins_base44/.
Certification gates (see docstring history in git):
  [A] exhaustive root-set enumeration: EXACTLY the advertised roots, all mate-in-2
  [B] every advertised branch line replays to proven checkmate
  [C] every advertised reply is legal; every advertised root is a true root
  [D] attacker lines have odd ply count
  [E] post-write read-back verification; any exception = refusal, never crash
  Verdicts are structured (bool, str) -- no string matching on log prose.

Usage:
    python build_twins_fixtures.py            # write (refuses overwrite)
    python build_twins_fixtures.py --force    # overwrite
    python build_twins_fixtures.py --dry-run  # verify only
"""

import argparse
import json
import pathlib
import sys
from datetime import date

import chess

from twins_data import TWINS

OUT_DIR = pathlib.Path("twins_base44")
INDEX_NAME = "fixtures_index.json"
SCHEMA_VERSION = "twins-fixture/1.0"

PROVENANCE = {
    "generated_by": "Base44 app-builder (lookbeyondtheobviousmove.com)",
    "inspiration": "Bilalic, McLeod & Gobet (2008) Einstellung effect in chess",
    "acquired": "2026-11-10",
    "verified_by": "build_twins_fixtures.py v0.3",
    "verification": (
        "exhaustive first-move enumeration: exactly 2 mating roots, both mate-in-2; "
        "all advertised branch lines replayed to proven checkmate"
    ),
}


def any_mate_in_1(board):
    """True if the side to move has at least one checkmating move."""
    for mv in list(board.legal_moves):
        board.push(mv)
        mate = board.is_checkmate()
        board.pop()
        if mate:
            return True
    return False


def mating_roots(fen):
    """Enumerate ALL first moves that force mate in <= 2.
    Returns {san: length}. Mate-in-2 acceptance requires EVERY
    defender reply to be mated in 1.
    """
    board = chess.Board(fen)
    roots = {}
    for mv in list(board.legal_moves):
        san = board.san(mv)
        board.push(mv)
        if board.is_checkmate():
            roots[san] = 1
        elif not board.is_game_over():
            covered = True
            for reply in list(board.legal_moves):
                board.push(reply)
                if not any_mate_in_1(board):
                    covered = False
                board.pop()
                if not covered:
                    break
            if covered:
                roots[san] = 2
        board.pop()
    return roots


def replay_line(fen, sans):
    """Replay a SAN sequence from fen; return final board."""
    board = chess.Board(fen)
    for san in sans:
        try:
            board.push_san(san)
        except ValueError as exc:
            raise ValueError(f"illegal SAN '{san}' in line {sans}: {exc}") from exc
    return board


def verify_twin(twin):
    """Checks [A]-[D]. Returns list of (ok: bool, message: str)."""
    results = []
    try:
        enum = mating_roots(twin["fen"])
    except ValueError as exc:
        return [(False, f"[A] FAIL invalid FEN: {exc}")]
    advertised = {r["move"] for r in twin["roots"]}
    if set(enum.keys()) != advertised:
        results.append((False, f"[A] FAIL root set mismatch: enumerated "
                                f"{sorted(enum)} vs advertised {sorted(advertised)}"))
    else:
        results.append((True, f"[A] PASS root set exactly {sorted(enum)}"))
    if any(v == 1 for v in enum.values()):
        results.append((False, "[A] FAIL mate-in-1 root present (degenerate)"))
    if any(v != 2 for v in enum.values()):
        results.append((False, f"[A] FAIL unexpected root length in {enum}"))

    for root in twin["roots"]:
        tag_root = f"'{root['move']}' ({root['role']})"
        rb = chess.Board(twin["fen"])
        try:
            root_move = rb.parse_san(root["move"])
        except ValueError:
            results.append((False, f"[C] FAIL root move {tag_root} not legal"))
            continue
        rb.push(root_move)
        legal_replies = {rb.san(m) for m in rb.legal_moves}
        if root["move"] not in enum:
            results.append((False, f"[C] FAIL advertised root {tag_root} "
                                   "is not a mating root in enumeration"))
        for reply, line in root["branches"].items():
            tag = f"branch {tag_root} ...{reply}"
            if reply not in legal_replies:
                results.append((False, f"[C] FAIL {tag}: reply not legal after root"))
                continue
            if line[0] != root["move"] or line[1] != reply:
                results.append((False, f"[B] FAIL {tag}: line prefix mismatch {line[:2]}"))
                continue
            if len(line) % 2 != 1:
                results.append((False, f"[D] FAIL {tag}: even ply count {len(line)}"))
                continue
            try:
                final = replay_line(twin["fen"], line)
            except ValueError as exc:
                results.append((False, f"[B] FAIL {tag}: {exc}"))
                continue
            if final.is_checkmate():
                results.append((True, f"[B] PASS {tag}: replayed to proven mate"))
            else:
                results.append((False, f"[B] FAIL {tag}: line does not end in mate"))
    return results


def build_record(twin):
    familiar = next(r for r in twin["roots"] if r["role"] == "familiar")
    familiar_main = next(iter(familiar["branches"].values()))
    mate_length = (len(familiar_main) + 1) // 2  # attacker-moves convention
    return {
        "id": twin["id"],
        "name": twin["name"],
        "paradigm": "twin",
        "fen": twin["fen"],
        "first_move": familiar["move"],
        "declared": {"mate_length": mate_length, "root_count": len(twin["roots"])},
        "lines": {"familiar": familiar_main},
        "roots": twin["roots"],
        "provenance": dict(PROVENANCE, built=date.today().isoformat()),
        "schema": SCHEMA_VERSION,
    }


def verify_record_file(path):
    """[E] read-back verification. Any exception = refusal, never a crash."""
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
        enum = mating_roots(rec["fen"])
        if set(enum.keys()) != {r["move"] for r in rec["roots"]}:
            return False, f"{path.name}: read-back root set mismatch"
        if any(v != 2 for v in enum.values()):
            return False, f"{path.name}: read-back unexpected root length"
        if rec["declared"]["mate_length"] != 2:
            return False, f"{path.name}: read-back mate_length != 2"
        for root in rec["roots"]:
            for reply, line in root["branches"].items():
                final = replay_line(rec["fen"], line)
                if not final.is_checkmate():
                    return False, f"{path.name}: read-back line {line[0]} ...{reply} no mate"
        return True, f"{path.name}: read-back verified (root set + all lines mate)"
    except Exception as exc:  # noqa: BLE001 -- read-back must never crash the run
        return False, f"{path.name}: read-back raised {type(exc).__name__}: {exc}"


def main():
    ap = argparse.ArgumentParser(description="Build twin fixtures (certified at birth)")
    ap.add_argument("--force", action="store_true", help="overwrite existing records")
    ap.add_argument("--dry-run", action="store_true",
                    help="verify everything, write nothing")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    written, failures = [], []

    print("build_twins_fixtures v0.3 -- twin-paradigm fixture builder (split edition)\n")
    for twin in TWINS:
        print(f"== {twin['id']} {twin['name']} ==")
        results = verify_twin(twin)
        for _, msg in results:
            print("   " + msg)
        if not all(ok for ok, _ in results):
            failures.append(twin["id"])
            print("   --> REFUSED: record not written\n")
            continue
        if args.dry_run:
            print("   --> verified (dry run, not written)\n")
            continue
        path = OUT_DIR / f"{twin['id']}.json"
        if path.exists() and not args.force:
            failures.append(twin["id"])
            print(f"   --> REFUSED: {path} exists (use --force)\n")
            continue
        path.write_text(
            json.dumps(build_record(twin), indent=2) + "\n", encoding="utf-8")
        rb_ok, rb_msg = verify_record_file(path)
        print(f"   --> wrote {path.name}; {rb_msg}")
        if rb_ok:
            written.append(path.name)
        else:
            failures.append(twin["id"])
        print()

    if not args.dry_run:
        index_path = OUT_DIR / INDEX_NAME
        index_path.write_text(json.dumps({
            "schema": SCHEMA_VERSION,
            "paradigm": "twin",
            "source": PROVENANCE["generated_by"],
            "built": date.today().isoformat(),
            "records": sorted(written),
            "count": len(written),
            "note": ("Exhaustively verified: each position has exactly two "
                     "mating roots, both mate-in-2; all branch lines end in "
                     "proven mate. Oracle note: these are twins -- the "
                     "shadow-doctrine check alt_first_move_mates rejects "
                     "them BY DESIGN; they are fixtures, not corpus records."),
        }, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {index_path} ({len(written)} record(s))")

    print(f"\n{len(written)} verified record(s) written"
          + (" (dry run)" if args.dry_run else "")
          + f", {len(failures)} refused/failed")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()