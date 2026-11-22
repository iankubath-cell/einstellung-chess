#!/usr/bin/env python3
"""adjudicate_base44.py v0.1.2 -- independent re-proof of Base44 duel exports.

v0.1.2 over v0.1.1 (dialect tolerance; strictness unchanged):
  1. `horizon` accepted as int (treated as maxMateMoves, plies = 2n-1),
     as the session-export object, or absent. The composer-lane export
     writes `"horizon": 3` -- v0.1.1 assumed the object form and crashed
     fail-closed on `hz.get`.
  2. Longest-defence evidence accepted from `longestDefence` OR
     `representative.defence` (composer-lane form). Absent in both ->
     missing_field, as before.
  3. `roots: null` tolerated in the informational line (composer-lane
     export writes null where sessions wrote a count).
  All chess checks unchanged: exact mate lengths by oracle.Solver,
  exhaustive defence coverage, constructive refutations, tie-set
  exactness, no mate-in-1, strict no-loud-mate-2 root tables.

Checks (fail-closed; each defence refuted constructively):
  invalid_fen        FEN parses; White to move; not in check; not terminal
  horizon_mismatch   horizon contradicts slowerLine.mateIn
  anatomy_unsupported derived quiet length is not 2
  fast_is_loud       quietKey keys are non-checking AND non-capturing
  key_not_mate_in_2  primary quiet key forces mate in exactly 2 (exhaustive)
  defences_not_exhaustive  logged defences != ALL legal replies after key
  defence_bad_san     a logged defence does not parse in this position
  defence_duplicate  two logged defences denote the same move
  defence_not_refuted      each defence answered by a logged mate that is
                           checkmate on the board
  mate_in_one        some root mates in 1
  tie_set_wrong     roots mating in 2 != exactly the claimed quietKey.keys
  no_contrast        a slower key is not a check
  slower_length_wrong  slower keys do not force exactly the declared length
  slower_replay_failed recorded line does not replay legally to checkmate
  slower_defence_mismatch line's second move != declared longest defence
  outcome_mismatch   record outcome is not 'verified'

Their node counts are compared informationally -- testimony, not evidence.
Exit codes: 0 = all PASS, 1 = any FAIL/UNPROVEN, 2 = usage/input error.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import chess
import oracle

BUDGET = 5_000_000

def adjudicate(rec):
    problems, info = [], []

    def bad(code, detail):
        problems.append((code, detail))

    # --- 0. schema presence
    for fld in ("fen", "quietKey", "slowerLine"):
        if fld not in rec:
            return "FAIL", [("missing_field", fld)], info
    qk, sl = rec["quietKey"], rec["slowerLine"]
    for fld in ("primary", "defences"):
        if fld not in qk:
            return "FAIL", [("missing_field", f"quietKey.{fld}")], info
    for fld in ("primary", "moves"):
        if fld not in sl:
            return "FAIL", [("missing_field", f"slowerLine.{fld}")], info
    if rec.get("outcome") != "verified":
        bad("outcome_mismatch", f"outcome is {rec.get('outcome')!r}")

    # --- 1. derived lengths, horizon consistency (int | dict | absent)
    try:
        slow_n = int(sl.get("mateIn", 3))
    except (TypeError, ValueError):
        return "FAIL", [("missing_field", "slowerLine.mateIn")], info
    hz = rec.get("horizon")
    hz_moves = hz_plies = None
    if isinstance(hz, dict):
        hz_moves = int(hz.get("maxMateMoves", -1))
        hz_plies = int(hz.get("plies", -1))
    elif isinstance(hz, (int, float)):
        hz_moves = int(hz)
        hz_plies = 2 * hz_moves - 1
    if hz_moves is not None and (hz_moves != slow_n
                                 or hz_plies != 2 * slow_n - 1):
        bad("horizon_mismatch",
            f"horizon maxMateMoves={hz_moves}, plies={hz_plies} vs "
            f"mateIn={slow_n}")
    fast_n = slow_n - 1
    if fast_n != 2:
        return "FAIL", problems + [
            ("anatomy_unsupported",
             f"derived quiet length {fast_n}; only fast=2 duels are "
             f"adjudicated")], info

    # --- 2. board validity
    try:
        b0 = chess.Board(rec["fen"])
    except ValueError as e:
        return "FAIL", [("invalid_fen", str(e))], info
    if b0.turn != chess.WHITE or b0.is_check() or not b0.is_valid():
        bad("invalid_fen",
            f"turn={'W' if b0.turn else 'B'} check={b0.is_check()} "
            f"status={b0.status().name}")
        return "FAIL", problems, info

    S = oracle.Solver(BUDGET)
    try:
        # --- 3. primary quiet key: quiet, forces mate in exactly fast_n
        key = b0.parse_san(qk["primary"])
        if b0.gives_check(key) or b0.is_capture(key):
            bad("fast_is_loud",
                f"{qk['primary']} checks={b0.gives_check(key)} "
                f"captures={b0.is_capture(key)}")
        n_key = S.len_after(b0, key, fast_n)
        if n_key != fast_n:
            bad("key_not_mate_in_2", f"solver total = {n_key}")

        # --- 4. defence coverage on canonicalised moves
        b1 = b0.copy(stack=False)
        b1.push(key)
        legal = {b1.san(mv) for mv in b1.legal_moves}
        logged_canon = set()
        for d in qk["defences"]:
            try:
                dsan, msan = d["defence"], d["mate"]
            except (KeyError, TypeError) as e:
                bad("missing_field", f"defence entry lacks {e}")
                continue
            try:
                logged_canon.add(b1.san(b1.parse_san(dsan)))
            except ValueError:
                bad("defence_bad_san", f"{dsan!r} does not parse here")
        if len(logged_canon) != len(qk["defences"]):
            bad("defence_duplicate",
                f"{len(qk['defences'])} entries, "
                f"{len(logged_canon)} distinct moves")
        if logged_canon != legal:
            bad("defences_not_exhaustive",
                f"missing {sorted(legal - logged_canon)} "
                f"spurious {sorted(logged_canon - legal)}")

        # --- 5. constructive refutation of every logged defence
        for d in qk["defences"]:
            try:
                dsan, msan = d["defence"], d["mate"]
            except (KeyError, TypeError):
                continue
            b2 = b1.copy(stack=False)
            try:
                b2.push_san(dsan)
                b2.push_san(msan)
            except ValueError as e:
                bad("defence_bad_san", f"{dsan} -> {msan}: {e}")
                continue
            if not b2.is_checkmate():
                bad("defence_not_refuted",
                    f"{dsan} -> {msan} is not checkmate")

        # --- 6. root table: no mate-in-1; tie set disclosed exactly
        key_sans = set()
        for k in dict.fromkeys(list(qk.get("keys") or []) +
                               [qk["primary"]]):
            km = b0.parse_san(k)
            key_sans.add(b0.san(km))
            if b0.gives_check(km) or b0.is_capture(km):
                bad("fast_is_loud", f"tied key {k} is not quiet")
        roots_all = list(b0.legal_moves)
        mate_fast = set()
        for mv in roots_all:
            n = S.len_after(b0, mv, fast_n)
            if n == 1:
                bad("mate_in_one", b0.san(mv))
            elif n == fast_n:
                mate_fast.add(b0.san(mv))
        if mate_fast != key_sans:
            bad("tie_set_wrong",
                f"proved mate-in-{fast_n} roots {sorted(mate_fast)} vs "
                f"claimed {sorted(key_sans)}")

        # --- 7. slower line: checks, exact length, replays to mate
        for k in dict.fromkeys(list(sl.get("keys") or []) +
                               [sl["primary"]]):
            km = b0.parse_san(k)
            if not b0.gives_check(km):
                bad("no_contrast", f"{k} is not a check")
            ns = S.len_after(b0, km, slow_n)
            if ns != slow_n:
                bad("slower_length_wrong",
                    f"{k}: solver total = {ns}, declared {slow_n}")
        bl = b0.copy(stack=False)
        try:
            for s in sl["moves"]:
                bl.push_san(s)
        except ValueError as e:
            bad("slower_replay_failed", str(e))
        else:
            if not bl.is_checkmate():
                bad("slower_replay_failed", "line does not end in checkmate")
            if len(sl["moves"]) != 2 * slow_n - 1:
                bad("slower_length_wrong",
                    f"{len(sl['moves'])} plies recorded for mate in {slow_n}")
            long_def = sl.get("longestDefence")
            if long_def is None:
                rep = sl.get("representative")
                if isinstance(rep, dict):
                    long_def = rep.get("defence")
            if long_def is None:
                bad("missing_field", "slowerLine longest defence "
                    "(neither longestDefence nor representative.defence)")
            elif len(sl["moves"]) > 1 and sl["moves"][1] != long_def:
                bad("slower_defence_mismatch",
                    f"moves[1]={sl['moves'][1]}, declared {long_def}")

        # --- 8. informational: testimony vs our own measurements
        their_roots = rec.get("roots")
        info.append(f"roots ours {len(roots_all)}"
                    f"{' vs theirs ' + str(their_roots) if their_roots else ''};"
                    f" solver nodes ours {S.nodes}"
                    f"{' vs theirs ' + str(rec['nodes']) if rec.get('nodes') else ''};"
                    f" defences {len(qk['defences'])}")

    except oracle.BudgetExceeded:
        return "UNPROVEN", problems + [
            ("budget_exceeded", f"{BUDGET} nodes")], info
    except ValueError as e:
        return "FAIL", problems + [("invalid_san", str(e))], info

    return ("PASS" if not problems else "FAIL"), problems, info

def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"input file not found: {argv[1]}")
        return 2
    except json.JSONDecodeError as e:
        print(f"invalid JSON in {argv[1]}: {e}")
        return 2
    if isinstance(data, dict):
        data = [data]
    print(f"adjudicating {len(data)} record(s) from {argv[1]}\n")
    n = {"PASS": 0, "FAIL": 0, "UNPROVEN": 0}
    t0 = time.time()
    for i, rec in enumerate(data, 1):
        t1 = time.time()
        try:
            status, problems, info = adjudicate(rec)
        except Exception as e:  # fail-closed isolation per record
            status, problems, info = "FAIL", [(type(e).__name__, str(e))], []
        print(f"[{i:2}] {status:8} {rec.get('fen', '?')[:26]}  "
              f"({time.time() - t1:.1f}s)")
        for code, detail in problems:
            print(f"     {code}: {detail}")
        for line in info:
            print(f"     (info) {line}")
        n[status] += 1
    print(f"\n{n['PASS']}/{len(data)} PASS, {n['FAIL']} FAIL, "
          f"{n['UNPROVEN']} UNPROVEN in {time.time() - t0:.1f}s")
    return 0 if n["PASS"] == len(data) else 1

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv))