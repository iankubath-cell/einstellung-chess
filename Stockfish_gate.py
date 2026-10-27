#!/usr/bin/env python3
"""
Stockfish_gate.py -- cross-check verified corpus positions against python-chess and Stockfish.

What is checked, per position
  A  every recorded line replays legally and ends in checkmate
  B  structure checks (when enough lines exist):
     - same first move in all lines
     - at least one longer line than 'short'
     - if multiple longer lines exist, they fork at attacker's 2nd move
  C  for EVERY legal first move: shortest forced mate (cap 3) per python-chess
     vs Stockfish (restricted to that move). Expect:
     - none mates in 1 or 2
     - shared first move is the only one mating within 3
  D  branch checks on each recorded line:
     at each attacker move from move-2 onward, restrict Stockfish to the planned move;
     forced-mate length must equal attacker moves remaining on that line (both engines)
  E  defence sweeps:
     - after shared first move, every defender reply is mated within budget 2
     - after short-line second attacker move (if present), every defender reply is mated
       within budget 1

Controls (falsification):
  1) remove attacker queen -> nothing mates within 3
  2) remove each attacker non-king piece (one at a time) -> report which removals break
     the shared first move mating within 3 (derived key-piece set)

Usage:
  set STOCKFISH_PATH=C:\\path\\to\\stockfish.exe
  python Stockfish_gate.py [--depth 24] [--threads 1] [--hash 256]
  python Stockfish_gate.py --no-engine
  python Stockfish_gate.py --only C1,S1
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import chess
import chess.engine
import load_positions


# ---------------------------------------------------------------- python-chess solver

def ordered(b: chess.Board):
    return sorted(
        b.legal_moves,
        key=lambda m: (not b.gives_check(m), not b.is_capture(m))
    )


class Solver:
    """Plain forced-mate search. Attacker = side to move. Memoised on (EPD, depth)."""
    def __init__(self):
        self.m = {}

    def attacker_mates(self, b: chess.Board, n: int) -> bool:
        k = (b.epd(), n)
        if k in self.m:
            return self.m[k]
        res = False
        for mv in ordered(b):
            b.push(mv)
            if b.is_checkmate():
                res = True
            elif n > 1 and self.defender_loses(b, n - 1):
                res = True
            b.pop()
            if res:
                break
        self.m[k] = res
        return res

    def defender_loses(self, b: chess.Board, n: int) -> bool:
        moves = list(b.legal_moves)
        if not moves:
            return False  # stalemate is not a win
        for mv in moves:
            b.push(mv)
            ok = self.attacker_mates(b, n)
            b.pop()
            if not ok:
                return False
        return True

    def shortest(self, b: chess.Board, maxn: int) -> Optional[int]:
        for n in range(1, maxn + 1):
            if self.attacker_mates(b, n):
                return n
        return None

    def len_after(self, b: chess.Board, mv: chess.Move, maxn: int) -> Optional[int]:
        """
        Forced-mate length (attacker moves, counting mv) if attacker plays mv;
        None if > maxn.
        """
        b.push(mv)
        try:
            if b.is_checkmate():
                return 1
            for n in range(1, maxn):
                if self.defender_loses(b, n):
                    return n + 1
            return None
        finally:
            b.pop()


SOLVER = Solver()


# ---------------------------------------------------------------- engine side

def sf_len(
    eng: Optional[chess.engine.SimpleEngine],
    b: chess.Board,
    depth: int,
    root: Optional[chess.Move] = None,
    cap: Optional[int] = None
):
    """Stockfish forced-mate length for side to move (None if no mate / longer than cap)."""
    if eng is None:
        return "n/a"
    info = eng.analyse(
        b,
        chess.engine.Limit(depth=depth),
        root_moves=[root] if root else None
    )
    sc = info["score"].pov(b.turn)
    if sc.is_mate() and sc.mate() and sc.mate() > 0:
        k = sc.mate()
        return k if (cap is None or k <= cap) else None
    return None


# ---------------------------------------------------------------- reporting

FAILS = 0


def report(ok: bool, label: str, detail: str = ""):
    global FAILS
    if not ok:
        FAILS += 1
    print(f"{'PASS' if ok else 'FAIL':5} {label:62} {detail}")


def agree(py, sf):
    return sf == "n/a" or py == sf


def first_move_table(eng, b: chess.Board, depth: int, cap: int = 3):
    """{san: (py_len, sf_len)} for every legal first move."""
    t = {}
    for mv in list(b.legal_moves):
        san = b.san(mv)
        t[san] = (SOLVER.len_after(b, mv, cap), sf_len(eng, b, depth, mv, cap))
    return t


def sets_from(t):
    py = {n: sorted(s for s, (p, _) in t.items() if p is not None and p <= n) for n in (1, 2, 3)}
    sf = {n: sorted(s for s, (_, f) in t.items() if f not in (None, "n/a") and f <= n) for n in (1, 2, 3)}
    return py, sf


# ---------------------------------------------------------------- corpus loading

@dataclass
class GatePos:
    pid: str
    name: str
    fen: str
    lines: Dict[str, List[str]]  # key -> SAN list


def _line_items(pos) -> List[Tuple[str, List[str]]]:
    """
    Extract (key, san_list) from either dataclass-style line objects or dict-like lines.
    """
    out = []
    lines_obj = getattr(pos, "lines", None)
    if lines_obj is None:
        return out

    # dataclass/dict tolerant
    if isinstance(lines_obj, dict):
        iterable = lines_obj.items()
    else:
        iterable = []
        for k in dir(lines_obj):
            if k.startswith("_"):
                continue
            v = getattr(lines_obj, k)
            if hasattr(v, "san") or isinstance(v, dict):
                iterable.append((k, v))

    for k, v in iterable:
        if hasattr(v, "san"):
            san = list(v.san)
        elif isinstance(v, dict) and "san" in v:
            san = list(v["san"])
        else:
            continue
        out.append((k, san))
    return out


def load_verified_positions(only_ids: Optional[List[str]] = None) -> List[GatePos]:
    corpus = load_positions.load()
    selected: List[GatePos] = []
    for p in corpus.positions:
        pid = getattr(p, "id")
        status = getattr(p, "status", "")
        if status != "verified":
            continue
        if only_ids and pid not in only_ids:
            continue

        items = _line_items(p)
        lines = {k: san for k, san in items if san}
        if "short" not in lines:
            # fail-closed: verified position should have at least short line
            raise RuntimeError(f"{pid}: verified but no 'short' line found")
        if "familiar" not in lines:
            # allow S2-like cases; checks will degrade gracefully
            pass

        selected.append(
            GatePos(
                pid=pid,
                name=getattr(p, "name", ""),
                fen=getattr(p, "fen"),
                lines=lines
            )
        )
    return selected


# ---------------------------------------------------------------- per-position checks

def choose_line_keys(lines: Dict[str, List[str]]):
    short_key = "short" if "short" in lines else None
    fam_key = "familiar" if "familiar" in lines else None
    others = [k for k in lines.keys() if k not in {"short", "familiar"}]
    return short_key, fam_key, others


def attacker_len(san_line: List[str]) -> int:
    return (len(san_line) + 1) // 2


def check_position(eng, P: GatePos, depth: int):
    pid = P.pid
    b0 = chess.Board(P.fen)
    print(f"\n{pid} — {P.name}")
    print(f"FEN: {P.fen}  ({'White' if b0.turn else 'Black'} to move)")
    report(b0.is_valid() and not b0.is_check(), f"{pid} A  valid FEN, side to move not in check")

    # A: replay all lines
    for k, moves in P.lines.items():
        b = b0.copy()
        ok = True
        why = ""
        try:
            for m in moves:
                b.push_san(m)
        except Exception as e:
            ok = False
            why = str(e)
        report(ok and b.is_checkmate() and moves[-1].endswith("#"), f"{pid} A  line '{k}' replays and ends in mate", why)

    short_key, fam_key, other_keys = choose_line_keys(P.lines)
    short = P.lines[short_key]
    shared = short[0]

    # B: structure (graceful with partial coverage)
    report(all(v[0] == shared for v in P.lines.values()), f"{pid} B  same first move in all recorded lines", shared)

    longer = [k for k, v in P.lines.items() if attacker_len(v) > attacker_len(short)]
    report(len(longer) >= 1, f"{pid} B  at least one line strictly longer than short",
           f"short={attacker_len(short)} longer={[(k, attacker_len(P.lines[k])) for k in longer]}")

    # fork check only if we have at least one longer and enough plies
    fork_ok = True
    fork_detail = "n/a"
    if len(longer) >= 1 and len(short) >= 3 and len(P.lines[longer[0]]) >= 3:
        fork_ok = P.lines[longer[0]][2] != short[2]
        fork_detail = f"{longer[0]}:{P.lines[longer[0]][2]} vs short:{short[2]}"
    report(fork_ok, f"{pid} B  fork at attacker's 2nd move (where applicable)", fork_detail)

    # C: every legal first move
    t = first_move_table(eng, b0, depth)
    bad = {s: v for s, v in t.items() if not agree(*v)}
    report(not bad, f"{pid} C  python-chess vs Stockfish agree on all {len(t)} first moves",
           "" if not bad else f"DISAGREE: {bad}")

    py, sf = sets_from(t)
    report(py[1] == [] and (eng is None or sf[1] == []), f"{pid} C  no first move mates in 1", f"py={py[1]} sf={sf[1]}")
    report(py[2] == [] and (eng is None or sf[2] == []), f"{pid} C  no first move mates within 2", f"py={py[2]} sf={sf[2]}")
    report(py[3] == [shared] and (eng is None or sf[3] == [shared]),
           f"{pid} C  only the shared first move mates within 3", f"py={py[3]} sf={sf[3]}")

    # D: branch checks, planned move restricted
    seen = set()
    for k, moves in P.lines.items():
        b = b0.copy()
        for i, san in enumerate(moves):
            if i % 2 == 0 and i >= 2:  # attacker move from 2nd attacker move onward
                mv = b.parse_san(san)
                key = (b.epd(), mv.uci())
                if key not in seen:
                    seen.add(key)
                    remaining = (len(moves) - i + 1) // 2
                    p = SOLVER.len_after(b, mv, remaining + 1)
                    s = sf_len(eng, b, depth, mv)
                    ok = (p == remaining) and (s == "n/a" or s == remaining)
                    report(ok, f"{pid} D  {k:14} move {i//2+1} {san:7} forces mate in {remaining}", f"py={p} sf={s}")
            b.push_san(san)

    # E: defence sweeps
    def sweep(from_board: chess.Board, attacker_move: chess.Move, budget: int, label: str):
        b = from_board.copy()
        b.push(attacker_move)
        allok = True
        dis = []
        for r in list(b.legal_moves):
            a = b.copy()
            a.push(r)
            p = SOLVER.shortest(a, budget)
            s = sf_len(eng, a, depth, None, budget)
            if p is None or not agree(p, s):
                allok = False
                dis.append((b.san(r), p, s))
        report(allok, f"{pid} E  {label}: all {len(list(b.legal_moves))} defender replies mated within {budget}",
               "" if allok else f"PROBLEM: {dis}")

    # E1: after shared first move, budget 2
    b = b0.copy()
    first = b.parse_san(shared)
    sweep(b, first, 2, f"after {shared}")

    # E2: after short-line second attacker move, budget 1 (if short line long enough)
    if len(short) >= 3:
        b2 = b0.copy()
        for m in short[:2]:
            b2.push_san(m)
        sweep(b2, b2.parse_san(short[2]), 1, f"after {short[2]} (short line)")
    else:
        report(True, f"{pid} E  short-line second attacker move sweep skipped", "short line too short")

    return b0, shared


# ---------------------------------------------------------------- controls

def remove_attacker_queen_or_fail(b: chess.Board):
    queens = list(b.pieces(chess.QUEEN, b.turn))
    if not queens:
        raise RuntimeError("attacker has no queen; control-1 not applicable (fail-closed)")
    b.remove_piece_at(queens[0])


def key_piece_squares(base: chess.Board, shared: str, eng, depth: int) -> List[str]:
    """
    Derived key-piece set:
    attacker non-king piece removals that make shared first move stop mating within 3.
    """
    out = []
    for sq, pc in base.piece_map().items():
        if pc.color != base.turn:
            continue
        if pc.piece_type == chess.KING:
            continue
        b = base.copy()
        b.remove_piece_at(sq)
        if not b.is_valid():
            continue
        t = first_move_table(eng, b, depth)
        py, sf = sets_from(t)
        py_breaks = shared not in py[3]
        sf_breaks = (eng is None) or (shared not in sf[3])
        if py_breaks and sf_breaks:
            out.append(chess.square_name(sq))
    return sorted(out)


def run_controls(eng, depth: int, positions: List[GatePos]):
    print("\nFALSIFICATION CONTROLS (claims should break here; both sides must agree)")
    for P in positions:
        base = chess.Board(P.fen)
        short = P.lines["short"]
        shared = short[0]

        # 1: remove attacker queen -> nothing mates within 3
        b = base.copy()
        try:
            remove_attacker_queen_or_fail(b)
            t = first_move_table(eng, b, depth)
            py, sf = sets_from(t)
            bad = {s: v for s, v in t.items() if not agree(*v)}
            ok = (not bad) and py[3] == [] and (eng is None or sf[3] == [])
            report(ok,
                   f"{P.pid} ctl1 remove attacker queen: nothing mates within 3",
                   f"py={py[3]} sf={sf[3]}" + (f" DISAGREE {bad}" if bad else ""))
        except RuntimeError as e:
            report(False, f"{P.pid} ctl1 remove attacker queen", str(e))

        # 2: derived key-piece removals
        keys = key_piece_squares(base, shared, eng, depth)
        report(len(keys) > 0,
               f"{P.pid} ctl2 derived key-piece set non-empty (shared move breaks when removed)",
               f"key_squares={keys}")


# ---------------------------------------------------------------- main

def parse_only(s: Optional[str]) -> Optional[List[str]]:
    if not s:
        return None
    ids = [x.strip() for x in s.split(",") if x.strip()]
    return ids or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=os.environ.get("STOCKFISH_PATH"))
    ap.add_argument("--depth", type=int, default=24)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--hash", type=int, default=256)
    ap.add_argument("--no-engine", action="store_true")
    ap.add_argument("--only", default=None, help="comma-separated IDs (e.g. C1,S1,S2)")
    ap.add_argument("--skip-controls", action="store_true")
    a = ap.parse_args()

    only_ids = parse_only(a.only)
    positions = load_verified_positions(only_ids=only_ids)
    if not positions:
        sys.exit("No verified positions selected.")

    print("STOCKFISH GATE (loader-backed)" + ("  (python-chess only: --no-engine)" if a.no_engine else f"  depth={a.depth}"))
    print("-" * 110)
    print(f"Corpus verified selected: {len(positions)}  IDs={','.join([p.pid for p in positions])}")

    eng = None
    if not a.no_engine:
        if not a.engine or not os.path.isfile(a.engine):
            sys.exit("Set STOCKFISH_PATH (or --engine) to a valid Stockfish binary, or use --no-engine.")
        eng = chess.engine.SimpleEngine.popen_uci(a.engine)
        try:
            eng.configure({"Threads": a.threads, "Hash": a.hash})
        except Exception:
            pass

    try:
        for P in positions:
            check_position(eng, P, a.depth)
        if not a.skip_controls:
            run_controls(eng, a.depth, positions)
    finally:
        if eng:
            eng.quit()

    print("-" * 110)
    if FAILS == 0 and not a.no_engine:
        print("All checks passed; python-chess and Stockfish agree everywhere.")
    elif FAILS == 0:
        print("python-chess side passed (no engine run).")
    else:
        print(f"{FAILS} check(s) FAILED.")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()