#!/usr/bin/env python3
"""corner_window.py v0.1 -- boundary-anchoring test for certified duel positions.

QUESTION.  For a certified duel position on the 8x8 board: if every piece OUTSIDE a w x w window is deleted
(the board stays 8x8; kings are never deleted), is the position still a duel?  Compare windows that sit in a
board corner with windows that touch one board edge or none.  If duels need real board walls, corner windows
should survive more often than edge windows, and edge windows more often than interior ones.

PRE-REGISTERED DEFINITIONS (fixed before any certified position was run; do not tune after seeing results)
  Position       white to move; 8x8; no castling or en passant (pawnless family).
  Duel (strict)  1. no root move mates in 1;
                 2. no LOUD root (gives check or captures) forces mate within 2;
                 3. at least one QUIET root (neither check nor capture) forces mate in exactly 2;
                 4. at least one CHECKING root forces mate in exactly 3.
                 "Forces mate in n" = oracle.Solver.len_after(board, root, 3) == n; stalemate is not a win.
                 Reject code = the first failed condition in the order above:
                 mate_in_1, loud_mate_in_2, no_quiet_mate_in_2, no_checking_mate_in_3.
  Verdicts       DUEL / NOT_DUEL(code) / UNKNOWN (solver budget exhausted; never counted as either)
                 INVALID(code): not testable -- black king in check with white to move, white king in check
                 (excluded, as in the census), or any other illegal position.  Counted separately, never as a failure.
                 KINGS_NOT_IN_WINDOW: a king lies outside the window, so the net does not "fit"; not tested.
  Windows        w x w sub-squares of the 8x8 board for w = 2..7, every placement (r0, f0 in 0..8-w).
                 class corner   = contains a board corner square (4 windows per w);
                 class edge     = touches exactly one board edge;
                 class interior = touches no board edge;
                 w = 8 is the identity window ("full").
  GATE           the identity window of every input position must come out DUEL.  If any does not, this script's
                 reading of the predicate disagrees with the position's certified status: the run is marked
                 GATE FAILED, the window results are NOT interpretable, and the exit code is 2.
  Per position   min_w_corner / min_w_edge / min_w_interior = smallest w < 8 with a surviving window of that class.
                 ANCHORED_CORNER   some corner window with w < 8 survives
                 NON_CORNER_ONLY   a surviving edge/interior window with w < 8 exists but no corner window does
                                   (a counterexample to boundary anchoring)
                 FULL_BOARD_ONLY   no window with w < 8 survives
                 UNRESOLVED        no survivor found and at least one window was UNKNOWN
  No significance threshold is applied; the pooled tables are descriptive.  Optional per-position keys
  (quiet_key, check_key) are checked separately: do the ORIGINAL keys still work in a surviving window.

INPUT   .json  list of {"id", "fen", optional "quiet_key", "check_key"} (or {"positions": [...]}), or
        .csv/.txt lines  id,fen[,quiet_key,check_key]  (SAN or UCI keys).
OUTPUT  a NEW directory (refuses to overwrite): results.json, per_position.csv, pooled_by_window.csv,
        findings.md, run_provenance.json, SHA256SUMS.txt (every output file; raw and LF-normalised input,
        oracle and script hashes are recorded in run_provenance.json).
This script only reads its inputs and writes into the new output directory.  Evidence status of any run:
the sandbox it ran in; only a run on the project machine counts as a project finding.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
from multiprocessing import Pool

import chess

VERSION = "0.1"
O = None            # the oracle module, loaded per process
BUDGET = 5_000_000


def sha(path, lf=False):
    b = open(path, "rb").read()
    if lf:
        b = b.replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("oracle_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["oracle_under_test"] = mod
    spec.loader.exec_module(mod)
    for n in ("Solver", "BudgetExceeded"):
        if not hasattr(mod, n):
            sys.exit(f"STOP: {path} has no {n}")
    return mod


def _init(oracle_path, budget):
    global O, BUDGET
    O = load_oracle(oracle_path)
    BUDGET = budget


# ------------------------------------------------------------------ the strict predicate
def classify(fen):
    """Return a dict: status DUEL / NOT_DUEL / UNKNOWN / INVALID, code, roots {uci: [len, loud, check]}."""
    b = chess.Board(fen)
    if b.turn != chess.WHITE:
        return {"status": "INVALID", "code": "black_to_move"}
    st = b.status()
    if st & chess.STATUS_OPPOSITE_CHECK:
        return {"status": "INVALID", "code": "black_king_in_check"}
    if not b.is_valid():
        return {"status": "INVALID", "code": "invalid_position:" + str(int(st))}
    if b.is_check():
        return {"status": "INVALID", "code": "white_in_check"}
    roots = list(b.legal_moves)
    if not roots:
        return {"status": "NOT_DUEL", "code": "no_legal_move", "roots": {}, "nodes": 0}
    S = O.Solver(BUDGET)
    info = {}
    try:
        for mv in roots:
            chk = b.gives_check(mv)
            loud = chk or b.is_capture(mv)
            info[mv.uci()] = [S.len_after(b, mv, 3), loud, chk]
    except O.BudgetExceeded:
        return {"status": "UNKNOWN", "code": "budget_exceeded", "nodes": S.nodes}
    rows = list(info.values())
    if any(L == 1 for L, _, _ in rows):
        code = "mate_in_1"
    elif any(loud and L == 2 for L, loud, _ in rows):
        code = "loud_mate_in_2"
    elif not any((not loud) and L == 2 for L, loud, _ in rows):
        code = "no_quiet_mate_in_2"
    elif not any(chk and L == 3 for L, _, chk in rows):
        code = "no_checking_mate_in_3"
    else:
        code = None
    return {"status": "DUEL" if code is None else "NOT_DUEL", "code": code, "roots": info, "nodes": S.nodes}


def _work(task):
    key, fen = task
    return key, classify(fen)


# ------------------------------------------------------------------ windows
def window_class(r0, f0, w):
    if w == 8:
        return "full", None
    rank_edges = (r0 == 0) + (r0 + w == 8)
    file_edges = (f0 == 0) + (f0 + w == 8)
    if rank_edges and file_edges:
        name = ("a" if f0 == 0 else "h") + ("1" if r0 == 0 else "8")
        return "corner", name
    return ("edge" if rank_edges + file_edges == 1 else "interior"), None


def cut(board, r0, f0, w):
    nb = chess.Board(None)
    nb.turn = chess.WHITE
    nb.castling_rights = 0
    for sq, p in board.piece_map().items():
        if r0 <= chess.square_rank(sq) < r0 + w and f0 <= chess.square_file(sq) < f0 + w:
            nb.set_piece_at(sq, p)
    return nb


def kings_inside(board, r0, f0, w):
    for col in (chess.WHITE, chess.BLACK):
        k = board.king(col)
        if k is None or not (r0 <= chess.square_rank(k) < r0 + w and f0 <= chess.square_file(k) < f0 + w):
            return False
    return True


def read_input(path):
    if path.lower().endswith(".json"):
        raw = json.load(open(path, encoding="utf-8"))
        raw = raw["positions"] if isinstance(raw, dict) else raw
        return [{"id": str(p["id"]), "fen": p["fen"], "quiet_key": p.get("quiet_key"), "check_key": p.get("check_key")}
                for p in raw]
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split(",")]
        out.append({"id": parts[0], "fen": parts[1], "quiet_key": parts[2] if len(parts) > 2 and parts[2] else None,
                    "check_key": parts[3] if len(parts) > 3 and parts[3] else None})
    return out


def key_to_uci(board, key):
    if not key:
        return None
    try:
        mv = chess.Move.from_uci(key)
        if mv in board.legal_moves:
            return mv.uci()
    except ValueError:
        pass
    try:
        return board.parse_san(key).uci()
    except ValueError:
        return "unparseable"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("input")
    ap.add_argument("--oracle", required=True, help="path to the project's oracle.py (uses Solver, BudgetExceeded)")
    ap.add_argument("--outdir", required=True, help="NEW directory for the outputs; refused if it exists")
    ap.add_argument("--budget", type=int, default=5_000_000)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    if os.path.exists(a.outdir):
        sys.exit(f"STOP: {a.outdir} already exists; choose a new name (evidence is never overwritten).")
    positions = read_input(a.input)
    t0 = time.time()

    # ---- build the task list (identity + every window with both kings inside)
    tasks, meta, skipped = [], {}, {}
    for i, p in enumerate(positions):
        b = chess.Board(p["fen"])
        p["_board"] = b
        for w in range(2, 9):
            for r0 in range(0, 9 - w):
                for f0 in range(0, 9 - w):
                    cls, corner = window_class(r0, f0, w)
                    k = (i, w, r0, f0)
                    meta[k] = (cls, corner)
                    if w < 8 and not kings_inside(b, r0, f0, w):
                        skipped[k] = {"status": "KINGS_NOT_IN_WINDOW"}
                        continue
                    nb = b if w == 8 else cut(b, r0, f0, w)
                    tasks.append((k, nb.fen()))
    print(f"{len(positions)} positions, {len(tasks)} windows to classify ({len(skipped)} skipped: king outside)", flush=True)
    done = {}
    if a.workers > 1:
        with Pool(a.workers, initializer=_init, initargs=(a.oracle, a.budget)) as pool:
            for n, (k, res) in enumerate(pool.imap_unordered(_work, tasks, chunksize=4), 1):
                done[k] = res
                if n % 200 == 0:
                    print(f"  {n}/{len(tasks)}", flush=True)
    else:
        _init(a.oracle, a.budget)
        for n, t in enumerate(tasks, 1):
            k, res = _work(t)
            done[k] = res
            if n % 200 == 0:
                print(f"  {n}/{len(tasks)}", flush=True)
    done.update(skipped)

    # ---- assemble per-position results
    results, gate_bad = [], []
    pooled = {}
    for i, p in enumerate(positions):
        b = p["_board"]
        q_uci, c_uci = key_to_uci(b, p["quiet_key"]), key_to_uci(b, p["check_key"])
        ident = done[(i, 8, 0, 0)]
        if ident["status"] != "DUEL":
            gate_bad.append({"id": p["id"], "fen": p["fen"], "status": ident["status"], "code": ident.get("code")})
        wins, mins, unknown = [], {"corner": None, "edge": None, "interior": None}, 0
        for w in range(2, 8):
            for r0 in range(0, 9 - w):
                for f0 in range(0, 9 - w):
                    k = (i, w, r0, f0)
                    cls, corner = meta[k]
                    r = done[k]
                    keys_ok = None
                    if r["status"] == "DUEL" and (q_uci or c_uci):
                        ok_q = (q_uci is None) or (q_uci in r["roots"] and r["roots"][q_uci][0] == 2 and not r["roots"][q_uci][1])
                        ok_c = (c_uci is None) or (c_uci in r["roots"] and r["roots"][c_uci][0] == 3 and r["roots"][c_uci][2])
                        keys_ok = bool(ok_q and ok_c)
                    wins.append({"w": w, "r0": r0, "f0": f0, "class": cls, "corner": corner, "status": r["status"],
                                 "code": r.get("code"), "nodes": r.get("nodes"), "original_keys_still_work": keys_ok})
                    pk = (w, cls)
                    row = pooled.setdefault(pk, {"tested": 0, "duel": 0, "not_duel": 0, "unknown": 0, "invalid": 0, "kings_outside": 0})
                    if r["status"] == "DUEL":
                        row["tested"] += 1; row["duel"] += 1
                        if mins[cls] is None or w < mins[cls]:
                            mins[cls] = w
                    elif r["status"] == "NOT_DUEL":
                        row["tested"] += 1; row["not_duel"] += 1
                    elif r["status"] == "UNKNOWN":
                        row["unknown"] += 1; unknown += 1
                    elif r["status"] == "INVALID":
                        row["invalid"] += 1
                    else:
                        row["kings_outside"] += 1
        if mins["corner"] is not None:
            verdict = "ANCHORED_CORNER"
        elif mins["edge"] is not None or mins["interior"] is not None:
            verdict = "NON_CORNER_ONLY"
        elif unknown:
            verdict = f"UNRESOLVED({unknown} windows UNKNOWN)"
        else:
            verdict = "FULL_BOARD_ONLY"
        results.append({"id": p["id"], "fen": p["fen"], "pieces": len(b.piece_map()), "identity_window": ident["status"],
                        "min_w_corner": mins["corner"], "min_w_edge": mins["edge"], "min_w_interior": mins["interior"],
                        "verdict": verdict, "windows": wins})
    gate_ok = not gate_bad

    # ---- write outputs
    os.makedirs(a.outdir)
    out = lambda n: os.path.join(a.outdir, n)
    json.dump({"script_version": VERSION, "gate_ok": gate_ok, "gate_failures": gate_bad, "results": results},
              open(out("results.json"), "w", encoding="utf-8"), indent=1)
    with open(out("per_position.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "pieces", "identity_window", "min_w_corner", "min_w_edge", "min_w_interior", "verdict", "fen"])
        for r in results:
            wr.writerow([r["id"], r["pieces"], r["identity_window"], r["min_w_corner"], r["min_w_edge"], r["min_w_interior"],
                         r["verdict"], r["fen"]])
    with open(out("pooled_by_window.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["w", "class", "tested", "duel", "survival_rate", "not_duel", "unknown", "invalid", "kings_not_in_window"])
        for (w, cls), r in sorted(pooled.items(), key=lambda x: (x[0][0], x[0][1])):
            rate = f"{r['duel'] / r['tested']:.4f}" if r["tested"] else ""
            wr.writerow([w, cls, r["tested"], r["duel"], rate, r["not_duel"], r["unknown"], r["invalid"], r["kings_outside"]])
    verdicts = {}
    for r in results:
        verdicts.setdefault(r["verdict"].split("(")[0], []).append(r)
    with open(out("findings.md"), "w", encoding="utf-8") as f:
        f.write(f"# corner_window v{VERSION} findings\n\n")
        f.write(f"Input: {os.path.basename(a.input)}  positions: {len(results)}  windows classified: {len(tasks)}\n\n")
        if not gate_ok:
            f.write("## GATE FAILED -- window results are NOT interpretable\n\n"
                    "The identity window of these positions did not come out DUEL, so this script's reading of the strict "
                    "predicate disagrees with their certified status:\n\n")
            for g in gate_bad:
                f.write(f"- {g['id']}: {g['status']} {g['code']}  {g['fen']}\n")
            f.write("\n")
        else:
            f.write("Gate passed: every identity window is DUEL under this script's reading of the predicate.\n\n")
        f.write("## Per-position verdicts\n\n| verdict | count |\n|---|---|\n")
        for v, rs in sorted(verdicts.items()):
            f.write(f"| {v} | {len(rs)} |\n")
        f.write("\n## Positions that do NOT survive in any corner window with w < 8 (recorded as findings)\n\n")
        bad = [r for r in results if r["verdict"] != "ANCHORED_CORNER"]
        if not bad:
            f.write("None: every position has a surviving corner window with w < 8.\n")
        for r in bad:
            f.write(f"- {r['id']}  {r['verdict']}  min_w corner/edge/interior = {r['min_w_corner']}/{r['min_w_edge']}/"
                    f"{r['min_w_interior']}  {r['fen']}\n")
        f.write("\nA position failing corner survival is a result about that position's geometry, not a defect in its "
                "certification.  Pooled rates by window size and class are in pooled_by_window.csv.\n")
    prov = {"script": os.path.abspath(__file__), "script_sha256_raw": sha(__file__), "script_sha256_lf": sha(__file__, True),
            "oracle": os.path.abspath(a.oracle), "oracle_sha256_raw": sha(a.oracle), "oracle_sha256_lf": sha(a.oracle, True),
            "input": os.path.abspath(a.input), "input_sha256_raw": sha(a.input), "input_sha256_lf": sha(a.input, True),
            "budget": a.budget, "workers": a.workers, "python": platform.python_version(), "python_chess": chess.__version__,
            "platform": platform.platform(), "seconds": round(time.time() - t0, 1), "gate_ok": gate_ok,
            "command": sys.argv}
    json.dump(prov, open(out("run_provenance.json"), "w", encoding="utf-8"), indent=1)
    names = sorted(n for n in os.listdir(a.outdir))
    with open(out("SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        for n in names:
            f.write(f"{sha(out(n))}  {n}\n")
    print(open(out("findings.md"), encoding="utf-8").read())
    print("outputs:", a.outdir)
    print(open(out("SHA256SUMS.txt")).read())
    return 0 if gate_ok else 2


if __name__ == "__main__":
    sys.exit(main())