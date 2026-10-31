#!/usr/bin/env python3
"""oracle.py -- verdicts on Einstellung candidates (v0.2, first piece of the composer).

A *candidate* is: a FEN, the declared shared first move (SAN), and the declared
forced-mate lengths of the lines it claims (e.g. short=3, familiar=5).  SAN
lines are optional; when given they are replayed and checked node by node.

The oracle answers PASS / FAIL / UNKNOWN, with machine-readable reject codes.

  PASS     every check passed (see `evidence_tier` for who witnessed it)
  FAIL     at least one check failed (see `codes`, most important first)
  UNKNOWN  the node budget ran out before a verdict -- NOT a pass

Proof asymmetry (why there is a node budget and an UNKNOWN):
  * a mate found is a proof of that mate;
  * "nothing mates within N" is proven here only by exhaustive search to the
    stated horizon, and only if the budget was not exhausted.

Evidence tiers:
  python-only   verdict rests on the bundled exhaustive solver alone
  two-engine    solver AND Stockfish (root_moves-restricted) agreed everywhere

This module does not touch Stockfish_gate.py, which stays frozen as the
certified reference.  The solver below is the same algorithm, with a node
budget added.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import chess

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"

# Most important first. A verdict lists every code that fired, in this order.
CODES = (
    "invalid_fen",
    "invalid_first_move",
    "line_replay_failed",
    "shared_first_move_broken",
    "declared_length_mismatch",
    "mate_in_1",
    "no_forced_mate",
    "refuted_defence",
    "faster_mate_leak",
    "alt_first_move_mates",
    "engine_disagree",
    "budget_exceeded",
    "horizon_uncertified",
)

DEFAULT_BUDGET = 5_000_000


class BudgetExceeded(Exception):
    pass


class StopJudging(Exception):
    """Raised in fast mode at the first failed check."""


# --------------------------------------------------------------------------- solver

def _ordered(b: chess.Board):
    return sorted(b.legal_moves, key=lambda m: (not b.gives_check(m), not b.is_capture(m)))


class Solver:
    """Forced-mate search, attacker = side to move. Memoised on (EPD, depth)."""

    def __init__(self, budget: int = DEFAULT_BUDGET):
        self.m: Dict[tuple, bool] = {}
        self.nodes = 0
        self.budget = budget

    def attacker_mates(self, b: chess.Board, n: int) -> bool:
        k = (b.epd(), n)
        if k in self.m:
            return self.m[k]
        self.nodes += 1
        if self.nodes > self.budget:
            raise BudgetExceeded()
        res = False
        for mv in _ordered(b):
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

    def len_after(self, b: chess.Board, mv: chess.Move, maxn: int) -> Optional[int]:
        """Forced-mate length counting `mv` itself; None if no forced mate within maxn."""
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


# --------------------------------------------------------------------------- engine side

def sf_len(eng, b: chess.Board, depth: int, root: Optional[chess.Move], cap: Optional[int]):
    """Stockfish forced-mate length for the side to move, restricted to `root`.
    None = no mate found (or longer than cap). NOTE: engine absence of a mate is
    never a proof; only agreement with the exhaustive solver counts as evidence."""
    import chess.engine
    info = eng.analyse(b, chess.engine.Limit(depth=depth), root_moves=[root] if root else None)
    sc = info["score"].pov(b.turn)
    if sc.is_mate() and sc.mate() and sc.mate() > 0:
        k = sc.mate()
        return k if (cap is None or k <= cap) else None
    return None


def open_engine(path: str, threads: int = 1, hash_mb: int = 256):
    """Open a UCI engine and RECORD what actually happened (id and applied options),
    so reproducibility never depends on assumed defaults."""
    import chess.engine
    eng = chess.engine.SimpleEngine.popen_uci(path)
    info = {"engine_id": str(eng.id.get("name", "unknown")),
            "engine_author": str(eng.id.get("author", "unknown"))}
    for name, val in (("Threads", threads), ("Hash", hash_mb)):
        try:
            eng.configure({name: val})
            info[name.lower()] = f"{val} (applied)"
        except Exception as e:  # engine lacks the option
            info[name.lower()] = f"{val} requested, NOT applied ({type(e).__name__})"
    return eng, info


# --------------------------------------------------------------------------- data model

@dataclass
class Candidate:
    id: str
    fen: str
    first_move: str                       # SAN, the declared shared first move
    declared: Dict[str, int]              # line key -> declared mate length (moves)
    lines: Dict[str, List[str]] = field(default_factory=dict)  # optional SAN lines


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Verdict:
    id: str
    status: str = PASS
    codes: List[str] = field(default_factory=list)
    checks: List[Check] = field(default_factory=list)
    nodes: int = 0
    budget: int = DEFAULT_BUDGET
    evidence_tier: str = "python-only"
    caveats: List[str] = field(default_factory=list)
    fast: bool = False
    meta: Dict[str, str] = field(default_factory=dict)

    @property
    def primary(self) -> Optional[str]:
        return self.codes[0] if self.codes else None

    def add(self, name: str, ok: bool, detail: str = "", code: Optional[str] = None):
        self.checks.append(Check(name, ok, detail))
        if not ok:
            if self.status != UNKNOWN:
                self.status = FAIL
            if code and code not in self.codes:
                self.codes.append(code)
            if self.fast:
                raise StopJudging()

    def finish(self):
        if self.status == PASS and self.caveats:
            self.status = UNKNOWN          # a pass with unproven claims is not a pass
            self.codes.append("horizon_uncertified")
        self.codes.sort(key=CODES.index)


# --------------------------------------------------------------------------- the oracle

def judge(c: Candidate, budget: int = DEFAULT_BUDGET, engine=None, depth: int = 24,
          engine_info: Optional[Dict[str, str]] = None, fast: bool = False) -> Verdict:
    """fast=True stops at the first failed check (for search loops): the verdict then
    lists only that first failure, not every failure."""
    v = Verdict(id=c.id, budget=budget, fast=fast)
    v.meta = {"python": sys.version.split()[0], "python_chess": chess.__version__,
              "engine_depth": str(depth) if engine else "none", "solver_budget": str(budget)}
    v.meta.update(engine_info or {})
    v.meta["fast"] = str(fast)
    S = Solver(budget)
    try:
        _judge(c, S, v, engine, depth)
    except StopJudging:
        pass
    except BudgetExceeded:
        v.status = UNKNOWN
        if "budget_exceeded" not in v.codes:
            v.codes.append("budget_exceeded")
        v.checks.append(Check("budget", False, f"node budget {budget} exhausted"))
    v.nodes = S.nodes
    if engine is not None and v.status == PASS:
        v.evidence_tier = "two-engine"
    v.finish()
    return v


def _judge(c: Candidate, S: Solver, v: Verdict, eng, depth: int):
    # --- 0. board and declared first move
    try:
        b0 = chess.Board(c.fen)
        valid = b0.is_valid() and not b0.is_check()
    except ValueError:
        valid = False
    v.add("fen valid, side to move not in check", valid, code="invalid_fen")
    if not valid:
        return
    try:
        first = b0.parse_san(c.first_move)
    except ValueError as e:
        v.add("declared first move legal", False, str(e), code="invalid_first_move")
        return

    lmin, lmax = min(c.declared.values()), max(c.declared.values())

    # --- 1. recorded lines: replay, shared first move, declared length
    for key, san in c.lines.items():
        b = b0.copy()
        why = ""
        try:
            for s in san:
                b.push_san(s)
        except ValueError as e:
            why = str(e)
        v.add(f"line '{key}' replays and ends in mate", not why and b.is_checkmate(), why,
              code="line_replay_failed")
        v.add(f"line '{key}' starts with the shared first move", san[0] == c.first_move, san[0],
              code="shared_first_move_broken")
        if key in c.declared:
            v.add(f"line '{key}' length matches declared {c.declared[key]}",
                  (len(san) + 1) // 2 == c.declared[key], f"recorded {(len(san) + 1) // 2}",
                  code="declared_length_mismatch")

    # --- 2. mate in 1 anywhere (the 'shortcut' check)
    m1 = []
    for mv in list(b0.legal_moves):
        b0.push(mv)
        if b0.is_checkmate():
            m1.append(b0.peek())
        b0.pop()
    m1_san = [b0.san(m) for m in m1]
    v.add("no first move mates in 1", not (m1 and lmin > 1), f"mate in 1: {m1_san}", code="mate_in_1")

    # --- 3. first-move table. Horizon h = min(lmin, 3), as in the certified gate:
    #        alternatives that mate within h are rejected. Beyond 3 an exhaustive
    #        all-moves scan is too costly for the python solver, so it is NOT claimed.
    h = min(lmin, 3)
    table: Dict[str, Optional[int]] = {}
    for mv in list(b0.legal_moves):
        table[b0.san(mv)] = S.len_after(b0, mv, h)
    if h < lmin:
        v.caveats.append(f"alternative first moves checked only to {h} moves; "
                         f"uniqueness out to {lmin} not certified")

    if eng is not None:
        bad = {}
        for mv in list(b0.legal_moves):
            san = b0.san(mv)
            s = sf_len(eng, b0, depth, mv, h)
            if s != table[san]:
                bad[san] = (table[san], s)
        v.add(f"solver and engine agree on all {len(table)} first moves (horizon {h})", not bad,
              f"DISAGREE {bad}" if bad else "", code="engine_disagree")

    # --- 4. the declared first move, searched out to its own declared horizon lmin
    others = sorted(s for s, n in table.items() if s != c.first_move and n is not None and n <= h)
    v.add(f"no other first move mates within {h}", not others, f"{others}", code="alt_first_move_mates")

    Lstar = S.len_after(b0, first, lmin)
    if eng is not None:
        s_first = sf_len(eng, b0, depth, first, lmin)
        v.add(f"solver and engine agree on the declared first move out to {lmin}",
              s_first == Lstar, f"solver {Lstar}, engine {s_first}", code="engine_disagree")
    if Lstar is None:
        # refuted_defence: a CHECK that some replies lose to and others escape (the
        # defender has a refutation). Anything else that fails is no_forced_mate.
        bb = b0.copy()
        bb.push(first)
        mated, escaped = [], []
        for r in list(bb.legal_moves):
            bb.push(r)
            (mated if S.attacker_mates(bb, lmin - 1) else escaped).append(bb.peek().uci())
            bb.pop()
        if b0.gives_check(first) and mated and escaped:
            v.add(f"declared first move forces mate within {lmin}", False,
                  f"{len(mated)} replies mated, {len(escaped)} escape", code="refuted_defence")
        else:
            v.add(f"declared first move forces mate within {lmin}", False,
                  "no defender reply is mated" if not mated else "", code="no_forced_mate")
    elif Lstar < lmin:
        v.add(f"declared first move's shortest mate is {lmin}", False,
              f"shortest is {Lstar}", code="faster_mate_leak")
    else:
        v.add(f"declared first move's shortest mate is exactly {lmin}", True, f"{c.first_move}")

    # --- 5. node-by-node exactness along each recorded line (from attacker move 2)
    seen = set()
    for key, san in c.lines.items():
        b = b0.copy()
        try:
            for i, s in enumerate(san):
                if i % 2 == 0 and i >= 2:
                    mv = b.parse_san(s)
                    remaining = (len(san) - i + 1) // 2
                    k = (b.epd(), mv.uci())
                    if k not in seen:
                        seen.add(k)
                        p = S.len_after(b, mv, remaining + 1)
                        if p is None or p > remaining:
                            code = "refuted_defence"
                        elif p < remaining:
                            code = "faster_mate_leak"
                        else:
                            code = None
                        ok = p == remaining
                        det = f"declared remaining {remaining}, solver {p}"
                        if eng is not None:
                            s_len = sf_len(eng, b, depth, mv, None)
                            det += f", engine {s_len}"
                            if s_len != p:
                                v.add(f"{key}: solver and engine agree at move {i // 2 + 1} {s}", False,
                                      det, code="engine_disagree")
                        v.add(f"{key}: move {i // 2 + 1} {s} forces mate in exactly {remaining}", ok, det,
                              code=code)
                b.push_san(s)
        except ValueError:
            pass  # replay failure already recorded above


# --------------------------------------------------------------------------- corpus runner

def load_candidates(canonical: Path, rejects: Path):
    """Yield (Candidate, expectation) where expectation is 'PASS' or a reject code."""
    raw = json.loads(canonical.read_text(encoding="utf-8"))
    for p in raw["positions"]:
        lines = {k: v["san"] for k, v in p["lines"].items() if v.get("san")}
        declared = {k: p["lines"][k]["length"] for k in ("short", "familiar") if k in p["lines"]}
        if p["status"] == "verified":
            yield Candidate(p["id"], p["fen"], p["first_move"], declared, lines), "PASS"
        elif p["status"] == "verified_puzzle_only":
            code = p["gate_results"]["expected_rejection"]
            yield Candidate(p["id"], p["fen"], p["first_move"], declared, lines), code
    grave = {g["id"]: g for g in raw["graveyard"]}
    for r in json.loads(rejects.read_text(encoding="utf-8"))["candidates"]:
        g = grave[r["graveyard_id"]]
        assert g["expected_rejection"] == r["expect"], (
            f"{g['id']}: canonical says {g['expected_rejection']} but fixtures say {r['expect']}")
        yield Candidate(g["id"], g["fen"], r["first_move"], r["declared"], r.get("lines", {})), r["expect"]


def _fmt(v: Verdict) -> str:
    return f"{v.status:7} codes={v.codes} nodes={v.nodes} tier={v.evidence_tier}"


def cmd_corpus(a) -> int:
    eng, info = (open_engine(a.engine) if a.engine else (None, None))
    bad = 0
    try:
        for cand, expect in load_candidates(Path(a.canonical), Path(a.rejects)):
            v = judge(cand, budget=a.budget, engine=eng, depth=a.depth, engine_info=info, fast=a.fast)
            if expect == "PASS":
                ok = v.status == PASS
            else:
                ok = v.status == FAIL and expect in v.codes
            bad += not ok
            print(f"{'ok  ' if ok else 'WRONG'} {cand.id:3} expect={expect:17} -> {_fmt(v)}")
            if not ok or a.verbose:
                for ch in v.checks:
                    if not ch.ok or a.verbose:
                        print(f"        {'PASS' if ch.ok else 'FAIL'} {ch.name}  {ch.detail}")
    finally:
        if eng:
            eng.quit()
    print(f"\nrun provenance: {v.meta}")
    print(f"{'ALL FIXTURES BEHAVE AS EXPECTED' if not bad else str(bad) + ' FIXTURE(S) WRONG'}")
    return 1 if bad else 0


def cmd_verify(a) -> int:
    declared = {k: int(n) for k, n in (x.split("=") for x in a.declared.split(","))}
    lines = {}
    for x in a.line or []:
        k, s = x.split("=", 1)
        lines[k] = s.split()
    eng, info = (open_engine(a.engine) if a.engine else (None, None))
    try:
        v = judge(Candidate("cli", a.fen, a.first, declared, lines), budget=a.budget, engine=eng,
                  depth=a.depth, engine_info=info, fast=a.fast)
    finally:
        if eng:
            eng.quit()
    print(_fmt(v))
    for ch in v.checks:
        print(f"  {'PASS' if ch.ok else 'FAIL'} {ch.name}  {ch.detail}")
    for cv in v.caveats:
        print(f"  CAVEAT {cv}")
    print(f"  provenance: {v.meta}")
    return {PASS: 0, FAIL: 1, UNKNOWN: 3}[v.status]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="oracle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    here = Path(__file__).resolve().parent

    pc = sub.add_parser("corpus", help="run the accept/reject fixture suite")
    pc.add_argument("--canonical", default=str(here / "positions" / "canonical.json"))
    pc.add_argument("--rejects", default=str(here / "fixtures" / "rejects.json"))
    pc.add_argument("--engine", default=None)
    pc.add_argument("--depth", type=int, default=24)
    pc.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    pc.add_argument("--verbose", action="store_true")
    pc.add_argument("--fast", action="store_true", help="stop each candidate at its first failed check")
    pc.set_defaults(fn=cmd_corpus)

    pv = sub.add_parser("verify", help="judge one candidate")
    pv.add_argument("--fen", required=True)
    pv.add_argument("--first", required=True, help="declared shared first move, SAN")
    pv.add_argument("--declared", required=True, help="e.g. short=3,familiar=5")
    pv.add_argument("--line", action="append", help='key="SAN SAN ..." (repeatable)')
    pv.add_argument("--engine", default=None)
    pv.add_argument("--depth", type=int, default=24)
    pv.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    pv.add_argument("--fast", action="store_true")
    pv.set_defaults(fn=cmd_verify)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())