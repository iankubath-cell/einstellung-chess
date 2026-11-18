#!/usr/bin/env python3
r"""triage_base44_r2.py -- machine triage of the nine new Base44 positions.

Adjudicates by engine, never by caption. For each position (White to move):
  * m_best : best forced mate for White at probe depth (attacker POV)
  * survey: EVERY legal White move pushed and re-probed -> mate-after
            (0 = immediate mate; None = no forced mate found)
  * verdicts:
      TWIN-CANDIDATE   >= 2 distinct first moves still mate in m_best total
      DECOY-CANDIDATE  exactly one optimal first move, plus at least one
                       tempting capture that breaks or slows the win
      NO-MATE          no forced mate found at probe depth
    The optimal-move count uses ALL legal moves (needed for twin detection);
    only the temptation display is capture-biased (Base44's "juicy captures").

Depth-18 probes are hints, not proofs. Anything promising goes to the
exhaustive gates (find_twins.py / pipeline certify), never straight in.

Usage:
  python -u triage_base44_r2.py
  python -u triage_base44_r2.py --depth 12 --only tangled
"""
from __future__ import annotations

import argparse
import sys
import time

import chess
import chess.engine

DEFAULT_ENGINE = (r"C:/Users/44777/Downloads/"
                 r"stockfish-windows-x86-64-universal/stockfish/"
                 r"stockfish-windows-x86-64-universal.exe")

# Names are Base44's captions, kept as LABELS ONLY (not trusted descriptions)
POSITIONS = [
    ("tangled-rook",          "3r2k1/1p3ppp/8/1Q5r/8/8/8/4R1K1 w - - 0 1"),
    ("f7-key",                "rn4k1/5ppp/8/5NN1/1r6/1Q6/8/6K1 w - - 0 1"),
    ("distant-attacker",      "3r2k1/5ppp/p7/8/Q6r/8/8/4R1K1 w - - 0 1"),
    ("knights-screen",        "rn4k1/5ppp/2p5/5NN1/1rQ5/8/8/6K1 w - - 0 1"),
    ("knights-screen-locked", "r5k1/5ppp/2p5/n4NN1/1rQ5/8/8/6K1 w - - 0 1"),
    ("queen-on-a4",           "6k1/5ppp/8/8/q7/8/5PPP/3QR1K1 w - - 0 1"),
    ("guarded-square",        "6k1/2q2ppp/8/5Q2/8/2R5/5PPP/6K1 w - - 0 1"),
    ("free-rook",             "6k1/5ppp/3N1Q2/8/8/6r1/5PPP/6K1 w - - 0 1"),
    ("rook-on-a5",            "2q3k1/5ppp/8/r4N2/8/8/3Q1PPP/6K1 w - - 0 1"),
    ("sacrifice-g8",   "r4r1k/pp1nb1pp/2pp3N/4N3/8/8/QPP2PPP/2BR2K1 w - - 0 1"),
    ("own-rook-way",   "5r1k/pp1n1Rpp/2p1Q2N/1b2p3/P7/8/1P3PPP/3R2K1 w - - 0 1"),
    ("pawn-on-h7",     "5r1k/pp1n1Ppp/2pQp3/4N3/8/8/PPP2PP1/2B3K1 w - - 0 1"),
    ("second-rook",    "5rk1/pp3ppp/3n4/5N2/2B4R/8/PP3PK1/R7 w - - 0 1"),
    ("king-steps-out", "r1b3rk/pp2n1pp/2pp4/4R3/6RQ/8/PP3PP1/2B3K1 w - - 0 1"),
]

PIECE_NAMES = {chess.PAWN: "p", chess.KNIGHT: "N", chess.BISHOP: "B",
               chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K"}


def mate_pov(eng, board, pov, depth):
    try:
        info = eng.analyse(board, chess.engine.Limit(depth=depth),
                           info=chess.engine.INFO_ALL)
    except chess.engine.EngineTerminatedError:
        raise SystemExit("engine died mid-triage; rerun the remaining "
                         "positions with --only <name>")
    if "score" not in info:
        return None
    return info["score"].pov(pov).mate()


def triage_position(name, fen, eng, depth):
    board = chess.Board(fen)
    if board.status() != chess.STATUS_VALID:
        print(f"\n=== {name}: INVALID POSITION ({board.status()!r}) -- skipped")
        return
    print(f"\n=== {name}  ({fen})")
    t0 = time.time()
    m_best = mate_pov(eng, board, chess.WHITE, depth)
    if m_best is None or m_best <= 0:
        print(f"  NO-MATE at depth {depth}   [{time.time()-t0:.0f}s]")
        return
    rows = []
    for mv in board.legal_moves:
        san = board.san(mv)
        cap = board.is_capture(mv)
        piece = PIECE_NAMES.get(board.piece_type_at(mv.from_square), "?")
        board.push(mv)
        if board.is_checkmate():
            m_after = 0
        else:
            m_after = mate_pov(eng, board, chess.WHITE, depth)
        board.pop()
        rows.append((san, piece, cap, m_after))
    optimal = [r for r in rows if r[3] == m_best - 1]
    slower = [r for r in rows if r[3] is not None and r[3] > m_best - 1]
    broken = [r for r in rows if r[3] is None]
    print(f"  best: mate in {m_best} (White)   "
          f"[{len(rows)} moves surveyed, {time.time()-t0:.0f}s]")
    print(f"  optimal first moves ({len(optimal)}): "
          + ", ".join(f"{r[0]}" for r in sorted(optimal)) or "(none?!)")
    # temptation display: captures that break or slow the win
    broke_caps = sorted(r for r in broken if r[2])
    slow_caps = sorted((r for r in slower if r[2]), key=lambda r: r[3],
                       reverse=True)
    for san, piece, _cap, m_after in broke_caps[:6]:
        print(f"    tempting {san:8} BREAKS the win (no forced mate found)")
    for san, piece, _cap, m_after in slow_caps[:6]:
        print(f"    tempting {san:8} still mates, but total {m_after + 1}")
    if len(optimal) >= 2:
        verdict = "TWIN-CANDIDATE"
    elif len(optimal) == 1 and (broke_caps or slow_caps):
        verdict = "DECOY-CANDIDATE"
    else:
        verdict = "UNCLASSIFIED"
    if m_best < 2:
        verdict += "  [short < 2: below --short-min floor]"
    print(f"  verdict: {verdict}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="machine triage of the nine new Base44 positions")
    ap.add_argument("--engine", default=DEFAULT_ENGINE)
    ap.add_argument("--depth", type=int, default=18)
    ap.add_argument("--only", default=None,
                    help="run only positions whose name contains this substring")
    args = ap.parse_args(argv)
    eng = chess.engine.SimpleEngine.popen_uci(args.engine)
    try:
        for name, fen in POSITIONS:
            if args.only and args.only.lower() not in name.lower():
                continue
            triage_position(name, fen, eng, args.depth)
    finally:
        eng.quit()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())