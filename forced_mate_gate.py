#!/usr/bin/env python3
"""Forcedness (tree) gate over the canonical corpus.

After the first move of a line, EVERY legal defender reply must still lose
to a forced mate by the attacker within the line's budget.
  budget after reply = line.length - 1   (moves, attacker to move)
Scores are taken from the attacker's POV, so Black-to-move positions work.
Positions come from positions/canonical.json via load_positions.py.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import chess
import chess.engine

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from load_positions import CorpusError, Line, Position, load, validate  # noqa: E402


def resolve_engine_path(cli_path):
    path = cli_path or os.environ.get("STOCKFISH_PATH")
    if not path:
        raise RuntimeError("Use --engine PATH or set STOCKFISH_PATH.")
    if not os.path.isfile(path):
        raise RuntimeError(f"Stockfish binary not found: {path}")
    return path


def mate_for_attacker(engine, board, attacker, depth):
    """Returns (mate_in_moves or None, text). Positive = attacker mates."""
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    score = info.get("score")
    if score is None:
        raise RuntimeError("Engine analysis missing 'score'")
    s = score.pov(attacker)
    if s.is_mate():
        m = s.mate()
        return (m if m is not None and m > 0 else None), f"#{m:+d}" if m is not None else "mate(?)"
    cp = s.score()
    return None, "cp(?)" if cp is None else f"{cp / 100:+.2f}"


def within(m, budget, strict):
    return m == budget if strict else m <= budget


def check_line(engine, pos: Position, line: Line, depth, recheck, strict) -> dict:
    out = {"passed": False, "error": None, "failures": {}, "checked": 0, "target": None}

    if not line.expect_mate or line.length is None or not line.san:
        out["error"] = "line is a probe or has no length/SAN; not a forcedness target"
        return out
    if line.length < 2:
        out["error"] = "mate in 1 has no defender replies to check"
        return out

    target = line.length - 1
    out["target"] = target
    board = pos.board
    if board.turn != pos.attacker:
        out["error"] = "attacker is not the side to move in this FEN"
        return out
    try:
        board.push_san(line.san[0])
    except ValueError as e:
        out["error"] = f"illegal first move {line.san[0]!r}: {e}"
        return out

    replies = list(board.legal_moves)
    if not replies:
        out["error"] = "no legal defender replies (vacuous gate)"
        return out

    for reply in replies:
        reply_san = board.san(reply)
        board.push(reply)
        out["checked"] += 1
        try:
            if board.is_checkmate():
                out["failures"][reply_san] = "defender mates the attacker"
                continue
            if board.is_game_over():
                out["failures"][reply_san] = "terminal non-mate result"
                continue

            m, txt = mate_for_attacker(engine, board, pos.attacker, depth)
            if m is not None and within(m, target, strict):
                continue
            m2, txt2 = mate_for_attacker(engine, board, pos.attacker, recheck)
            if m2 is None:
                out["failures"][reply_san] = f"no forced mate ({txt} @d{depth}; {txt2} @d{recheck})"
            elif not within(m2, target, strict):
                op = "==" if strict else "<="
                out["failures"][reply_san] = f"mate in {m2} violates {op} {target} ({txt2} @d{recheck})"
        finally:
            board.pop()

    out["passed"] = not out["failures"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Forcedness gate over canonical corpus.")
    ap.add_argument("--engine")
    ap.add_argument("--depth", type=int, default=28)
    ap.add_argument("--recheck-depth", type=int, default=34)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--hash", type=int, default=256)
    ap.add_argument("--only", help="Substring filter on position ID or name")
    ap.add_argument("--lines", default="short",
                    help="Comma-separated line keys to check (default: short)")
    ap.add_argument("--strict-exact", action="store_true",
                    help="Require mate distance == budget instead of <= budget")
    args = ap.parse_args()

    if args.depth <= 0 or args.recheck_depth <= 0:
        print("Argument error: depths must be positive.")
        return 2

    try:
        engine_path = resolve_engine_path(args.engine)
    except RuntimeError as e:
        print(f"Engine path error: {e}")
        return 2

    try:
        corpus = load()
    except CorpusError as e:
        print(f"Corpus load error: {e}")
        return 2
    errors = [i for i in validate(corpus) if i.is_error]
    if errors:
        print("Corpus validation FAILED:")
        for i in errors:
            print(f"  {i}")
        return 1

    keys = [k.strip() for k in args.lines.split(",") if k.strip()]
    positions = [p for p in corpus.positions
                 if not args.only or args.only.lower() in f"{p.id} {p.name}".lower()]
    if not positions:
        print("No positions match --only filter.")
        return 2

    print("FORCED MATE GATE")
    print("-" * 78)
    print(f"Engine={engine_path}")
    print(f"Depth={args.depth} Recheck={args.recheck_depth} Threads={args.threads} "
          f"Hash={args.hash} StrictExact={args.strict_exact} Lines={keys}")

    failed = 0
    try:
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            try:
                engine.configure({"Hash": args.hash, "Threads": args.threads})
            except chess.engine.EngineError as e:
                print(f"Warning: could not configure engine ({e}); using defaults.")

            for pos in positions:
                side = "White" if pos.attacker == chess.WHITE else "Black"
                print(f"\n=== {pos.id} — {pos.name} (attacker: {side}) ===")
                for key in keys:
                    line = pos.lines.get(key)
                    if line is None:
                        print(f"  [{key}] SKIPPED: no such line")
                        if pos.status in ("verified", "tree_gate_passed"):
                            failed += 1
                        continue
                    r = check_line(engine, pos, line, args.depth,
                                   args.recheck_depth, args.strict_exact)
                    if r["error"]:
                        print(f"  [{key}] ERROR: {r['error']}")
                        failed += 1
                        continue
                    print(f"  [{key}] first move {line.san[0]}, budget after reply: "
                          f"mate in {r['target']}, replies checked: {r['checked']}, "
                          f"passed: {r['passed']}")
                    if not r["passed"]:
                        failed += 1
                        for san, why in r["failures"].items():
                            print(f"    - {san}: {why}")
    except (OSError, chess.engine.EngineError, chess.engine.EngineTerminatedError) as e:
        print(f"Fatal engine error: {e}")
        return 2

    print(f"\nDone. Failed checks: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())