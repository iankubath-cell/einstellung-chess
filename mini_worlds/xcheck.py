#!/usr/bin/env python3
"""Per-position cross-check: my C census verdict vs the project's oracle.Solver (via python-chess) on real 8x8 positions."""
import importlib.util, random, sys, time
from multiprocessing import Pool
import chess

spec = importlib.util.spec_from_file_location("his_oracle", "orc/his_oracle.py")
O = importlib.util.module_from_spec(spec); sys.modules["his_oracle"] = O; spec.loader.exec_module(O)

NAMES = {1: "degenerate", 2: "mate1", 3: "loud2", 4: "nomate2", 5: "quiet2_nocheck3", 6: "DUEL"}

def classify(fen):
    b = chess.Board(fen)
    if not b.is_valid():
        return "invalid"
    S = O.Solver(400_000)
    roots = list(b.legal_moves)
    if not roots:
        return 1
    try:
        info = []
        for mv in roots:
            loud = b.is_capture(mv) or b.gives_check(mv)
            chk = b.gives_check(mv)
            info.append((loud, chk, S.len_after(b, mv, 3)))
    except O.BudgetExceeded:
        return "budget"
    if any(L == 1 for _, _, L in info): return 2
    if any(loud and L == 2 for loud, _, L in info): return 3
    if not any((not loud) and L == 2 for loud, _, L in info): return 4
    return 6 if any(chk and L == 3 for _, chk, L in info) else 5

def work(line):
    fen, cat = line.rsplit(" ", 1)
    return fen, int(cat), classify(fen)

if __name__ == "__main__":
    random.seed(5)
    lines = []
    for k, cap in ((2, 400), (4, 350), (6, 250), (8, 150)):
        L = [x.strip() for x in open(f"dump_k{k}.txt") if x.strip()]
        duels = [x for x in L if x.endswith(" 6")]
        rest = [x for x in L if not x.endswith(" 6")]
        random.shuffle(rest)
        lines += duels + rest[:max(0, cap - len(duels))]          # keep EVERY duel the C code found, plus random others
    t = time.time()
    with Pool(2) as p:
        res = p.map(work, lines, chunksize=20)
    tab, bad = {}, []
    for fen, c, py in res:
        tab[(c, py)] = tab.get((c, py), 0) + 1
        if c != py: bad.append((fen, c, py))
    print(f"positions checked: {len(res)}  in {time.time()-t:.0f}s   disagreements: {len(bad)}")
    for (c, py), n in sorted(tab.items(), key=lambda x: str(x)):
        print(f"   C says {NAMES[c]:16} oracle.Solver says {NAMES.get(py, py):16} {n}")
    for x in bad[:10]: print("DISPUTE", x)
