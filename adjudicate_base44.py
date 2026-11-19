#!/usr/bin/env python3
"""adjudicate_base44.py v0.1.1 -- independent re-proof of Base44 duel exports.

v0.1.1 over v0.1 (bug-review pass):
  1. Quiet length DERIVED from slowerLine.mateIn (fast = slow - 1) and
     cross-checked against the horizon fields (maxMateMoves, plies),
     instead of silently assuming FAST = 2. Inconsistent metadata fails
     horizon_mismatch; a non-2 fast length fails anatomy_unsupported.
  2. Missing fields (quietKey, slowerLine, defences entries, moves)
     fail as missing_field instead of a bare KeyError.
  3. Defence coverage is compared on canonicalised moves: their SANs are
     parsed first (defence_bad_san if unparsable, defence_duplicate if
     two entries denote one move), so spelling differences between
     chess.js and python-chess cannot masquerade as missing/spurious.
  4. longestDefence absence is its own missing_field, not a nonsense
     comparison against None.
  5. Missing input file or invalid JSON exits 2 with a clear message.

Checks (fail-closed; each defence refuted constructively):
  invalid_fen        FEN parses; White to move; not in check; not terminal
  horizon_mismatch   horizon fields contradict slowerLine.mateIn
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

    # --- 0. schema presence (bare KeyErrors are not reject codes)
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

    # --- 1. derived lengths, horizon consistency
    try:
        slow_n = int(sl.get("mateIn", 3))
    except (TypeError, ValueError):
        return "FAIL", [("missing_field", "slowerLine.mateIn")], info
    hz = rec.get("horizon")
    if hz is not None:
        if (int(hz.get("maxMateMoves", -1)) != slow_n
                or int(hz.get("plies", -1)) != 2 * slow_n - 1):
            bad("horizon_mismatch",
                f"maxMateMoves={hz.get('maxMateMoves')}, "
                f"plies={hz.get('plies')} vs mateIn={slow_n}")
    else:
        info.append("no horizon field; slow length taken from mateIn")
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
                continue  # already reported above
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
            if "longestDefence" in sl:
                if (len(sl["moves"]) > 1
                        and sl["moves"][1] != sl["longestDefence"]):
                    bad("slower_defence_mismatch",
                        f"moves[1]={sl['moves'][1]}, "
                        f"declared {sl['longestDefence']}")
            else:
                bad("missing_field", "slowerLine.longestDefence")

        # --- 8. informational: testimony vs our own measurements
        info.append(f"roots ours {len(roots_all)} vs theirs "
                    f"{rec.get('roots')}; solver nodes ours {S.nodes} "
                    f"vs theirs {rec.get('nodes')}; defences "
                    f"{len(qk['defences'])}")

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