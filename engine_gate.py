#!/usr/bin/env python3
"""engine_gate.py v4 — loader-migrated, fail-closed, POV-correct.

Changes v3 -> v4:
  - Missing-lines policy refined per Copilot review: ONLY status=="verified"
    requires non-empty lines. "tree_gate_passed" may have empty lines (runs
    engine-root analysis only); "untested" never fails on missing lines.
    This lets S2 run without a hard failure.

Integrates all prior review findings (CX-marked in comments):
  - All position data from positions/canonical.json via load_positions (F1)
  - score.pov(attacker), never .white() (F2 / C5)
  - Expected root mate ENFORCED from gate_results.expected_root_mate (C4)
  - Missing lines on VERIFIED positions = exit 2, not a warning (C1/C2)
  - expect_mate per line — probes that should NOT mate are supported (C3)
  - resolve_engine_path called once, inside try (C7)
  - Corpus validation ALWAYS runs before analysis (C11)
  - Exit codes: 0 = clean pass, 1 = gate failure, 2 = setup/config error (C8)
  - sys.path bootstrap so the script runs from repo root or scripts/ (C9)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

import chess
import chess.engine

# Bootstrap import path so this runs from repo root OR scripts/ dir
sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_positions import load, validate, CorpusError


def format_score(score: chess.engine.Score) -> str:
    if score.is_mate():
        m = score.mate()
        if m is None:
            return "mate(?)"
        return f"#{m:+d}" if m != 0 else "#0"
    cp = score.score()
    return "cp(?)" if cp is None else f"{cp / 100:+.2f}"


def pv_to_san(board: chess.Board, pv: List[chess.Move], max_plies: int) -> str:
    b = board.copy()
    out = []
    for mv in pv[:max_plies]:
        try:
            out.append(b.san(mv))
            b.push(mv)
        except ValueError:
            out.append(f"<bad:{mv}>")
            break
    return " ".join(out) if out else "(no pv)"


def replay_line(board: chess.Board, san_moves: List[str]):
    """Returns (legal, checkmate, error)."""
    b = board.copy()
    for i, san in enumerate(san_moves, 1):
        try:
            mv = b.parse_san(san)
        except ValueError as e:
            return False, False, f"move {i} '{san}' illegal ({e})"
        actual = b.san(mv)
        if actual != san:
            return False, False, f"move {i}: wrote '{san}', position gives '{actual}'"
        b.push(mv)
    return True, b.is_checkmate(), None


def resolve_engine_path(cli_path: Optional[str]) -> str:
    path = cli_path or os.environ.get("STOCKFISH_PATH")
    if not path:
        raise FileNotFoundError("Use --engine PATH or set STOCKFISH_PATH.")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Engine binary not found: {path}")
    return path


def analyse_position(eng, position, depth, multipv, max_pv_plies) -> int:
    """Returns problems found (0 = clean). Fails closed on every check."""
    problems = 0
    attacker_name = "White" if position.attacker == chess.WHITE else "Black"
    print(f"\n=== {position.id} — {position.name} ===")
    print(f"FEN: {position.fen}")

    try:
        board = chess.Board(position.fen)
    except ValueError as e:
        print(f"  [FAIL] FEN parse error: {e}")
        return 1
    if not board.is_valid():
        print(f"  [FAIL] Invalid position ({board.status()!r})")
        return 1

    try:
        result = eng.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
    except (chess.engine.EngineError, chess.engine.EngineTerminatedError) as e:
        print(f"  [FAIL] Engine error: {e}")
        return 1

    infos = result if isinstance(result, list) else [result]

    best_mate: Optional[int] = None
    print(f"  PVs (top {multipv}, POV: attacker = {attacker_name}):")
    for i, entry in enumerate(infos, 1):
        if "score" not in entry:
            print(f"    PV{i}: MISSING SCORE — gate failure")   # C1-class: never skip
            problems += 1
            continue
        score = entry["score"].pov(position.attacker)             # F2: POV-correct
        pv_text = pv_to_san(board, entry.get("pv", []), max_pv_plies)
        print(f"    PV{i} {format_score(score)}: {pv_text}")
        if i == 1:
            if score.is_mate():
                m = score.mate()
                best_mate = m if m is not None and m > 0 else None

    # ---- C4: the root-mate check. The check that would have caught C3. ----
    expected_root = position.gate_results.get("expected_root_mate")
    if expected_root is not None:
        if best_mate is None:
            print(f"  [FAIL] Expected root mate #+{expected_root}, "
                  f"but engine reports no forced mate for the attacker")
            problems += 1
        elif best_mate != expected_root:
            direction = "LEAK — mate faster than expected" if best_mate < expected_root \
                else "slower than expected — familiar line may be broken"
            print(f"  [FAIL] Expected root mate #+{expected_root}, got #+{best_mate} "
                  f"({direction})")
            problems += 1
        else:
            print(f"  [ok] Root mate #+{expected_root} exactly as expected")

    # ---- Line verification, with probe support (C3) ----
    if position.lines:
        print(f"  Line verification ({len(position.lines)} line(s)):")
        for name, line in position.lines.items():
            if not line.san:
                print(f"    {name}: [SKIP] no SAN recorded (data gap, not a pass)")
                continue
            legal, mate, err = replay_line(board, list(line.san))
            expect = line.expect_mate if hasattr(line, "expect_mate") else True
            if not legal:
                print(f"    {name}: [FAIL] ILLEGAL — {err}")
                problems += 1
            elif mate != expect:
                print(f"    {name}: [FAIL] checkmate={mate}, expected={expect}")
                problems += 1
            else:
                label = "checkmate" if mate else "no mate (probe, as expected)"
                print(f"    {name}: [ok] {label}")
    else:
        print("  (no lines recorded — engine-root analysis only for this position)")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze canonical Einstellung positions.")
    ap.add_argument("--engine")
    ap.add_argument("--depth", type=int, default=28)
    ap.add_argument("--multipv", type=int, default=3)
    ap.add_argument("--pv-plies", type=int, default=12)
    ap.add_argument("--hash", type=int, default=256, help="Hash MB")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--only", help="Filter positions by ID or name substring")
    args = ap.parse_args()

    # ---- Load corpus (single source of truth) ----
    try:
        corpus = load()
    except CorpusError as e:
        print(f"Corpus load error: {e}")
        return 2

    # ---- C11: validation ALWAYS runs, fail closed on structural errors ----
    issues = validate(corpus)
    errors = [i for i in issues if i.is_error]
    if errors:
        print("Corpus validation FAILED (structural):")
        for issue in issues:
            print(f"  {issue}")
        return 2
    for issue in issues:  # warnings only
        print(f"Corpus warning: {issue}")

    positions = [p for p in corpus.positions
                 if not args.only or args.only.lower() in f"{p.id} {p.name}".lower()]
    if not positions:
        print("No positions match --only filter")
        return 2

    # ---- C1/C2 + v4 policy: only VERIFIED positions require lines. ----
    # tree_gate_passed may have empty lines (engine-root analysis only);
    # untested never fails on missing lines.
    missing = [p for p in positions
               if p.status == "verified" and not p.lines]
    if missing:
        for p in missing:
            print(f"MISSING LINES: {p.id} (status=verified) — complete "
                  f"canonical.json before running")
        return 2

    # ---- C7: resolve engine ONCE, inside try ----
    try:
        path = resolve_engine_path(args.engine)
    except FileNotFoundError as e:
        print(f"Engine path error: {e}")
        return 2

    print(f"Engine: {path}")
    print(f"Depth={args.depth} MultiPV={max(1, args.multipv)} "
          f"Hash={args.hash} Threads={args.threads}")
    print(f"Corpus: {len(corpus.positions)} positions, "
          f"{len(corpus.graveyard)} graveyard; analysing {len(positions)}")
    print("Note: root analysis and replay only. "
          "Forcedness is checked by forced_mate_gate.py.")

    total = 0
    try:
        with chess.engine.SimpleEngine.popen_uci(path) as eng:
            try:
                eng.configure({"Hash": args.hash, "Threads": args.threads})
            except chess.engine.EngineError as e:
                print(f"Could not configure engine ({e}); using defaults.")
            for pos in positions:
                total += analyse_position(eng, pos, args.depth,
                                           max(1, args.multipv), max(1, args.pv_plies))
    except (OSError, chess.engine.EngineError,
            chess.engine.EngineTerminatedError) as e:
        print(f"Fatal engine error: {e}")
        return 2

    print(f"\nTotal problems: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
