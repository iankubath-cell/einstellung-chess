#!/usr/bin/env python3
"""
stockfish_gate.py -- cross-check the three smothered-mate Einstellung positions
against Stockfish, flagging ANY disagreement with python-chess.

Usage (Windows):
    set STOCKFISH_PATH=C:\\path\\to\\stockfish.exe
    python stockfish_gate.py [--depth 18] [--threads 2] [--hash 256]
Dry run without an engine (python-chess side only):
    python stockfish_gate.py --no-engine

Needs only python-chess (pip install chess). Exit code 0 = every check passed.

What is checked, per position
  A  every line replays legally and ends in checkmate
  B  structure: same first move; familiar line strictly longer than the shorter
     lines; the lines fork at the attacker's 2nd move
  C  for EVERY legal first move: shortest forced mate (cap 3) per python-chess
     vs per Stockfish (restricted to that move). Expect: none mates in 1 or 2;
     the shared first move is the only one mating within 3.
  D  branch checks: at each attacker move on each line, the planned move is
     restricted for Stockfish; the forced-mate length must equal the number of
     attacker moves left on that line (both engines).
  E  defence sweep: after the shared first move, and after the shorter-line
     second move, every Black reply is mated within the expected budget
     (both engines, exact length compared).
Controls: mutated positions where the claim should break; both sides must agree.
"""
import argparse, os, sys
import chess, chess.engine

POSITIONS = [
 dict(id="P1", fen="r4k1r/pp2qppp/1p3n2/RB1b4/6n1/P7/1BP3PP/R2R2K1 b - - 0 1", bishop="d5",
      lines=dict(
        fam ="Qe3+ Kh1 Nf2+ Kg1 Nh3+ Kh1 Qg1+ Rxg1 Nf2#",
        alt1="Qe3+ Kh1 Qh3 Rd2 Qxh2#",
        alt2="Qe3+ Kh1 Qh3 Kg1 Qxg2#",
        side="Qe3+ Kf1 Nxh2#")),
 dict(id="P2", fen="1k2rrn1/pp4pp/5n1p/1N3b2/4B3/8/PPPQ2PP/R1K4R w - - 0 1", bishop="e4",
      lines=dict(
        fam ="Qd6+ Ka8 Nc7+ Kb8 Na6+ Ka8 Qb8+ Rxb8 Nc7#",
        alt1="Qd6+ Ka8 Qa6 Re7 Qxa7#",
        alt2="Qd6+ Ka8 Qa6 Kb8 Qxb7#",
        side="Qd6+ Kc8 Nxa7#")),
 dict(id="P3", fen="2k4r/pppq1pp1/5pp1/4b1B1/1n3B2/5N2/PP3PP1/1K2R1N1 b - - 0 1", bishop="e5",
      lines=dict(
        fam ="Qd3+ Ka1 Nc2+ Kb1 Na3+ Ka1 Qb1+ Rxb1 Nc2#",
        alt1="Qd3+ Ka1 Qa3 Re2 Qxa2#",
        alt2="Qd3+ Ka1 Qa3 Kb1 Qxb2#",
        side="Qd3+ Kc1 Nxa2#")),
]

# ---------------------------------------------------------------- python-chess solver
def ordered(b):
    return sorted(b.legal_moves, key=lambda m: (not b.gives_check(m), not b.is_capture(m)))

class Solver:
    """Plain forced-mate search. Attacker = side to move. Memoised on (EPD, depth)."""
    def __init__(self): self.m = {}
    def attacker_mates(self, b, n):
        k = (b.epd(), n)
        if k in self.m: return self.m[k]
        res = False
        for mv in ordered(b):
            b.push(mv)
            if b.is_checkmate(): res = True
            elif n > 1 and self.defender_loses(b, n - 1): res = True
            b.pop()
            if res: break
        self.m[k] = res
        return res
    def defender_loses(self, b, n):
        moves = list(b.legal_moves)
        if not moves: return False            # stalemate is not a win
        for mv in moves:
            b.push(mv); ok = self.attacker_mates(b, n); b.pop()
            if not ok: return False
        return True
    def shortest(self, b, maxn):
        for n in range(1, maxn + 1):
            if self.attacker_mates(b, n): return n
        return None
    def len_after(self, b, mv, maxn):
        """forced-mate length (attacker moves, counting mv) if the attacker plays mv; None if > maxn"""
        b.push(mv)
        try:
            if b.is_checkmate(): return 1
            for n in range(1, maxn):
                if self.defender_loses(b, n): return n + 1
            return None
        finally:
            b.pop()

SOLVER = Solver()

# ---------------------------------------------------------------- engine side
def sf_len(eng, b, depth, root=None, cap=None):
    """Stockfish forced-mate length for the side to move (None if no mate found / longer than cap)."""
    if eng is None: return "n/a"
    info = eng.analyse(b, chess.engine.Limit(depth=depth), root_moves=[root] if root else None)
    sc = info["score"].pov(b.turn)
    if sc.is_mate() and sc.mate() > 0:
        k = sc.mate()
        return k if (cap is None or k <= cap) else None
    return None

# ---------------------------------------------------------------- reporting
FAILS = 0
def report(ok, label, detail=""):
    global FAILS
    FAILS += (not ok)
    print(f"{'PASS' if ok else 'FAIL':5} {label:58} {detail}")

def agree(py, sf):
    return sf == "n/a" or py == sf

def first_move_table(eng, b, depth, cap=3):
    """{san: (py_len, sf_len)} for every legal first move"""
    t = {}
    for mv in list(b.legal_moves):
        san = b.san(mv)
        t[san] = (SOLVER.len_after(b, mv, cap), sf_len(eng, b, depth, mv, cap))
    return t

def sets_from(t):
    py = {n: sorted(s for s, (p, _) in t.items() if p is not None and p <= n) for n in (1, 2, 3)}
    sf = {n: sorted(s for s, (_, f) in t.items() if f not in (None, "n/a") and f <= n) for n in (1, 2, 3)}
    return py, sf

# ---------------------------------------------------------------- per-position checks
def check_position(eng, P, depth):
    pid = P["id"]; b0 = chess.Board(P["fen"])
    print(f"\n{pid}  {P['fen']}  ({'White' if b0.turn else 'Black'} to move)")
    report(b0.is_valid() and not b0.is_check(), f"{pid} A  valid FEN, side to move not in check")
    L = {k: v.split() for k, v in P["lines"].items()}
    # A: replay
    for k, moves in L.items():
        b = b0.copy(); ok = True; why = ""
        try:
            for m in moves: b.push_san(m)
        except Exception as e:
            ok = False; why = str(e)
        report(ok and b.is_checkmate() and moves[-1].endswith("#"), f"{pid} A  line '{k}' replays and ends in mate", why)
    # B: structure
    shared = L["fam"][0]
    report(all(v[0] == shared for v in L.values()), f"{pid} B  same first move in all lines", shared)
    report(len(L["fam"]) > len(L["alt1"]) and len(L["fam"]) > len(L["alt2"]),
           f"{pid} B  familiar strictly longer", f"{(len(L['fam'])+1)//2} vs {(len(L['alt1'])+1)//2} moves")
    report(L["fam"][2] != L["alt1"][2], f"{pid} B  fork at attacker's 2nd move", f"{L['fam'][2]} vs {L['alt1'][2]}")

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
    for k, moves in L.items():
        b = b0.copy()
        for i, san in enumerate(moves):
            if i % 2 == 0 and i >= 2:
                mv = b.parse_san(san)
                key = (b.epd(), mv.uci())
                if key not in seen:
                    seen.add(key)
                    remaining = (len(moves) - i + 1) // 2
                    p = SOLVER.len_after(b, mv, remaining + 1)
                    s = sf_len(eng, b, depth, mv)
                    ok = (p == remaining) and (s == "n/a" or s == remaining)
                    report(ok, f"{pid} D  {k:4} move {i//2+1} {san:6} forces mate in {remaining}", f"py={p} sf={s}")
            b.push_san(san)

    # E: defence sweeps
    def sweep(b, mv, budget, label):
        b = b.copy(); b.push(mv)
        rows = []; allok = True; dis = []
        for r in list(b.legal_moves):
            a = b.copy(); a.push(r)
            p = SOLVER.shortest(a, budget)
            s = sf_len(eng, a, depth, None, budget)
            rows.append(p)
            if p is None or not agree(p, s): allok = False; dis.append((b.san(r), p, s))
        report(allok, f"{pid} E  {label}: all {len(rows)} Black replies mated within {budget}",
               "" if allok else f"PROBLEM: {dis}")
    b = b0.copy(); first = b.parse_san(shared)
    sweep(b, first, 2, f"after {shared}")
    b2 = b0.copy()
    for m in L["alt1"][:2]: b2.push_san(m)
    sweep(b2, b2.parse_san(L["alt1"][2]), 1, f"after {L['alt1'][2]} (shorter line)")
    return b0

# ---------------------------------------------------------------- controls
def attacker_piece_sq(b, piece_type):
    for sq in b.pieces(piece_type, b.turn): return sq

def run_controls(eng, depth):
    print("\nFALSIFICATION CONTROLS (the claim should break here; both sides must agree)")
    for P in POSITIONS:
        base = chess.Board(P["fen"]); shared = P["lines"]["fam"].split()[0]
        # 1: remove attacker's queen -> nothing should mate within 3
        b = base.copy(); b.remove_piece_at(attacker_piece_sq(b, chess.QUEEN))
        t = first_move_table(eng, b, depth); py, sf = sets_from(t)
        bad = {s: v for s, v in t.items() if not agree(*v)}
        report(not bad and py[3] == [] and (eng is None or sf[3] == []),
               f"{P['id']} ctl remove attacker queen: nothing mates within 3", f"py={py[3]} sf={sf[3]}" + (f" DISAGREE {bad}" if bad else ""))
        # 2: remove attacker's key bishop -> shared first move must stop forcing mate in 3
        b = base.copy(); b.remove_piece_at(chess.parse_square(P["bishop"]))
        t = first_move_table(eng, b, depth); py, sf = sets_from(t)
        bad = {s: v for s, v in t.items() if not agree(*v)}
        report(not bad and shared not in py[3] and (eng is None or shared not in sf[3]),
               f"{P['id']} ctl remove attacker bishop {P['bishop']}: {shared} no longer mates in 3",
               f"py={py[3]} sf={sf[3]}" + (f" DISAGREE {bad}" if bad else ""))

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=os.environ.get("STOCKFISH_PATH"))
    ap.add_argument("--depth", type=int, default=18)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--hash", type=int, default=128)
    ap.add_argument("--no-engine", action="store_true")
    a = ap.parse_args()
    print("STOCKFISH GATE" + ("  (python-chess only: --no-engine)" if a.no_engine else f"  depth={a.depth}"))
    print("-" * 100)
    eng = None
    if not a.no_engine:
        if not a.engine or not os.path.isfile(a.engine):
            sys.exit("Set STOCKFISH_PATH (or --engine) to a valid Stockfish binary, or use --no-engine.")
        eng = chess.engine.SimpleEngine.popen_uci(a.engine)
        try: eng.configure({"Threads": a.threads, "Hash": a.hash})
        except Exception: pass
    try:
        for P in POSITIONS: check_position(eng, P, a.depth)
        run_controls(eng, a.depth)
    finally:
        if eng: eng.quit()
    print("-" * 100)
    print("All checks passed; python-chess and Stockfish agree everywhere." if not FAILS and not a.no_engine
          else ("python-chess side passed (no engine run)." if not FAILS else f"{FAILS} check(s) FAILED."))
    sys.exit(1 if FAILS else 0)

if __name__ == "__main__":
    main()