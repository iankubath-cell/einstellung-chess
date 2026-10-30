#!/usr/bin/env python3
"""Einstellung composer v0.1: decoration search around the corpus skeleton.

The search is a seeded random walk.  It starts from the corpus positions that
the oracle certifies (mapped to one canonical orientation, where they all share
one skeleton), mutates only the *decoration* (never the skeleton pieces), and
keeps a child only if oracle.py says PASS.  oracle.py is the sole judge:
this file never decides on its own that a position is sound.

What a survivor is: a position the python oracle accepts, with the same first
move, the same declared lengths (short 3 / familiar 5) and the same familiar
line as the corpus.  What it is not: engine-certified (run ``verify`` on a
machine with Stockfish), and not shown to catch human players (that is a
separate calibration).  Many survivors will be cosmetic variants of a corpus
position; each file records its distance from the nearest corpus position.

Modes:
    unguided   mutations drawn at random
    guided     after a FAIL/UNKNOWN, one repair mutation chosen by the reject code

Usage:
    python composer.py search   --mode guided --seed 1 --evals 400 --out raw_guided_1.json
    python composer.py finalize --raw raw_guided_1.json raw_unguided_1.json --out composed
    python composer.py verify   composed --engine PATH --depth 24 > verdicts.txt
"""
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess

import composer_skeleton as sk
import oracle

HERE = Path(__file__).resolve().parent
VERSION = "0.1"
DECLARED = {"short": 3, "familiar": 5}
SEARCH_BUDGET = 40_000          # solver nodes per candidate during search; over budget = UNKNOWN = rejected
MAX_PIECES = 22
CAPS = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}
ADD_WEIGHTS = [(chess.PAWN, 4), (chess.KNIGHT, 3), (chess.BISHOP, 3), (chess.ROOK, 2), (chess.QUEEN, 1)]
KIND_WEIGHTS = [("add", 35), ("move", 25), ("remove", 15), ("retype", 15), ("recolour", 10)]

# reject code -> preferred repair mutations (a hypothesis about what each failure means)
REPAIR = {
    "mate_in_1": ["add_black", "recolour_black", "remove_white"],
    "alt_first_move_mates": ["add_black", "recolour_black", "remove_white"],
    "faster_mate_leak": ["add_black", "recolour_black", "remove_white"],
    "no_forced_mate": ["remove_black", "add_white", "recolour_white"],
    "refuted_defence": ["remove_black", "add_white", "recolour_white"],
}
REPAIR_DEFAULT = ["remove_any"]


# ------------------------------------------------------------------ seeds

def lf_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def pos_key(b: chess.Board) -> str:
    """Symmetry-canonical key of a whole position."""
    return sk.canonical(b)[0]


def decoration_set(b: chess.Board, skel_squares: set) -> frozenset:
    return frozenset((chess.square_name(s), p.symbol()) for s, p in b.piece_map().items() if s not in skel_squares)


def load_seeds(canonical_json: Path):
    """Corpus positions the oracle certifies, in the canonical orientation of the shared skeleton."""
    raw = json.loads(canonical_json.read_text(encoding="utf-8"))
    seeds, frame_fen, first = [], None, None
    for p in raw["positions"]:
        if p["status"] != "verified":
            continue
        fam = p["lines"]["familiar"]["san"]
        s0 = sk.extract(p["id"], p["fen"], fam)
        t = s0.canonical_transform
        fen = sk.transform_fen(p["fen"], t)
        fam_t = sk.transform_san_line(p["fen"], fam, t)
        first_t = sk.transform_san_line(p["fen"], [p["first_move"]], t)[0]
        s1 = sk.extract(p["id"], fen, fam_t)
        assert frame_fen in (None, s1.frame_fen), f"{p['id']}: skeleton differs from the others"
        frame_fen = s1.frame_fen
        assert first in (None, first_t) and fam_t is not None
        first = first_t
        seeds.append({"id": p["id"], "fen": fen, "familiar": fam_t, "first": first_t, "skeleton": s1})
    return seeds


# --------------------------------------------------------------- mutations

def _count(b: chess.Board, colour: bool, pt: int) -> int:
    return len(b.pieces(pt, colour))


def _legal_square(sq: int, pt: int) -> bool:
    return not (pt == chess.PAWN and chess.square_rank(sq) in (0, 7))


def _wchoice(rng: random.Random, pairs):
    tot = sum(w for _, w in pairs)
    x = rng.uniform(0, tot)
    for v, w in pairs:
        x -= w
        if x <= 0:
            return v
    return pairs[-1][0]


def mutate(b: chess.Board, skel: set, rng: random.Random, kind: Optional[str] = None
           ) -> Optional[Tuple[chess.Board, str]]:
    """Return (new board, description) or None.  Skeleton squares are never touched."""
    b = b.copy()
    deco = [s for s in b.piece_map() if s not in skel]
    free = [s for s in chess.SQUARES if s not in skel and b.piece_at(s) is None]
    kinds = [kind] if kind else [_wchoice(rng, KIND_WEIGHTS)]
    k = kinds[0]
    colour_hint = None
    if k and "_" in k:                       # e.g. add_black, remove_white, recolour_black
        k, c = k.split("_")
        colour_hint = {"black": chess.BLACK, "white": chess.WHITE}.get(c)
        if c == "any":
            colour_hint = None
    name = lambda col: "white" if col else "black"
    if k == "add":
        if len(b.piece_map()) >= MAX_PIECES or not free:
            return None
        col = colour_hint if colour_hint is not None else rng.choice([chess.WHITE, chess.BLACK])
        pt = _wchoice(rng, ADD_WEIGHTS)
        sq = rng.choice(free)
        if not _legal_square(sq, pt) or _count(b, col, pt) >= CAPS[pt]:
            return None
        b.set_piece_at(sq, chess.Piece(pt, col))
        return b, f"add {name(col)} {chess.piece_symbol(pt).upper()} {chess.square_name(sq)}"
    cand = [s for s in deco if colour_hint is None or b.piece_at(s).color == colour_hint]
    if not cand:
        return None
    sq = rng.choice(cand)
    p = b.piece_at(sq)
    if k == "remove":
        b.remove_piece_at(sq)
        return b, f"remove {name(p.color)} {p.symbol().upper()} {chess.square_name(sq)}"
    if k == "move":
        if not free:
            return None
        to = rng.choice(free)
        if not _legal_square(to, p.piece_type):
            return None
        b.remove_piece_at(sq)
        b.set_piece_at(to, p)
        return b, f"move {name(p.color)} {p.symbol().upper()} {chess.square_name(sq)}->{chess.square_name(to)}"
    if k == "retype":
        pt = _wchoice(rng, ADD_WEIGHTS)
        if pt == p.piece_type or not _legal_square(sq, pt) or _count(b, p.color, pt) >= CAPS[pt]:
            return None
        b.set_piece_at(sq, chess.Piece(pt, p.color))
        return b, f"retype {name(p.color)} {p.symbol().upper()}->{chess.piece_symbol(pt).upper()} {chess.square_name(sq)}"
    if k == "recolour":
        if colour_hint is not None:          # recolour_black means: make a white piece black
            cand = [s for s in deco if b.piece_at(s).color != colour_hint]
            if not cand:
                return None
            sq = rng.choice(cand)
            p = b.piece_at(sq)
        col = not p.color
        if _count(b, col, p.piece_type) >= CAPS[p.piece_type]:
            return None
        b.set_piece_at(sq, chess.Piece(p.piece_type, col))
        return b, f"recolour {p.symbol().upper()} {name(p.color)}->{name(col)} {chess.square_name(sq)}"
    return None


# ------------------------------------------------------------------ judging

def judge_board(b: chess.Board, first: str, familiar: List[str], cid: str, fast: bool, budget: int):
    cand = oracle.Candidate(cid, b.fen(), first, dict(DECLARED), {"familiar": list(familiar)})
    return oracle.judge(cand, budget=budget, fast=fast)


def prefilter(b: chess.Board, first: str) -> bool:
    if not b.is_valid() or b.turn != chess.WHITE:
        return False
    try:
        mv = b.parse_san(first)
    except Exception:
        return False
    return b.gives_check(mv)


# ------------------------------------------------------------------- search

def cmd_search(a) -> int:
    seeds = load_seeds(Path(a.canonical))
    skel = {chess.parse_square(s) for s in seeds[0]["skeleton"].squares}
    first, familiar = seeds[0]["first"], seeds[0]["familiar"]
    rng = random.Random(a.seed)
    guided = a.mode == "guided"
    pool = [(chess.Board(s["fen"]), s["id"], []) for s in seeds]     # (board, name, lineage)
    seen = {pos_key(b): "corpus:" + n for b, n, _ in pool}
    corpus_decos = {n: decoration_set(b, skel) for b, n, _ in pool}
    stats = {"evals": 0, "prefilter_rejects": 0, "cache_hits": 0, "pass": 0, "codes": {}, "guided_repairs": 0,
             "guided_repair_passes": 0}
    survivors = []

    def evaluate(b: chess.Board, parent_lineage, desc, parent_fen, it, repair=False):
        k = pos_key(b)
        if k in seen:
            stats["cache_hits"] += 1
            return None
        if not prefilter(b, first):
            stats["prefilter_rejects"] += 1
            seen[k] = "prefilter"
            return None
        stats["evals"] += 1
        v = judge_board(b, first, familiar, f"s{a.seed}-{it}", fast=True, budget=SEARCH_BUDGET)
        seen[k] = v.status
        key = ",".join(v.codes) if v.codes else v.status
        stats["codes"][key] = stats["codes"].get(key, 0) + 1
        return v

    it = 0
    while stats["evals"] < a.evals and it < a.evals * 20:
        it += 1
        parent, pname, lineage = rng.choice(pool)
        child, desc = parent, []
        steps = rng.choice([1, 1, 2])
        ok = True
        for _ in range(steps):
            m = mutate(child, skel, rng)
            if m is None:
                ok = False
                break
            child, d = m
            desc.append(d)
        if not ok:
            continue
        v = evaluate(child, lineage, desc, parent.fen(), it)
        if v is None:
            continue
        cur, cur_desc, cur_v, depth = child, desc, v, 0
        # guided repair: up to two further mutations chosen by the reject code
        while guided and cur_v.status != oracle.PASS and depth < 2 and stats["evals"] < a.evals:
            codes = cur_v.codes or []
            prefs = REPAIR.get(codes[0], REPAIR_DEFAULT) if codes else REPAIR_DEFAULT
            m = mutate(cur, skel, rng, rng.choice(prefs))
            if m is None:
                break
            nxt, d = m
            stats["guided_repairs"] += 1
            v2 = evaluate(nxt, lineage, cur_desc + [d], parent.fen(), it, repair=True)
            if v2 is None:
                break
            cur, cur_desc, cur_v, depth = nxt, cur_desc + [d], v2, depth + 1
            if cur_v.status == oracle.PASS:
                stats["guided_repair_passes"] += 1
        if cur_v.status != oracle.PASS:
            continue
        stats["pass"] += 1
        step = {"parent_fen": parent.fen(), "parent": pname, "mutations": cur_desc, "verdict": "PASS (fast)"}
        name = f"{a.mode[0]}{a.seed}-{len(survivors) + 1}"
        pool.append((cur, name, lineage + [step]))
        dec = decoration_set(cur, skel)
        near = min(corpus_decos, key=lambda n: len(dec ^ corpus_decos[n]))
        survivors.append({"name": name, "fen": cur.fen(), "lineage": lineage + [step], "iteration": it,
                          "evals_so_far": stats["evals"], "nearest_corpus": near,
                          "distance": len(dec ^ corpus_decos[near])})
        print(f"[{a.mode} s{a.seed}] eval {stats['evals']:4}  PASS {name}  dist {survivors[-1]['distance']}  {'; '.join(cur_desc)}",
              flush=True)

    out = {"composer_version": VERSION, "mode": a.mode, "seed": a.seed, "evals_budget": a.evals,
           "first_move": first, "familiar": familiar, "declared": DECLARED, "search_budget_nodes": SEARCH_BUDGET,
           "skeleton_frame": seeds[0]["skeleton"].frame_fen, "stats": stats, "survivors": survivors}
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"done: {stats['evals']} evals, {stats['pass']} PASS (fast), stats: {stats}")
    return 0


# ----------------------------------------------------------------- finalize

def standard_san(fen: str, sans: List[str]) -> Tuple[List[str], List[str]]:
    """Replay lenient SAN and re-render it in standard SAN; also list the moves that capture."""
    b = chess.Board(fen)
    out, caps = [], []
    for s in sans:
        mv = b.parse_san(s)
        std = b.san(mv)
        out.append(std)
        if b.is_capture(mv):
            caps.append(std)
        b.push(mv)
    return out, caps


VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def authenticity(b: chess.Board, skel: set) -> dict:
    """Crude 'does this look like a real game position' measures.  RECORDED, NOT USED TO FILTER:
    the search ran without them, so filtering afterwards would be post-hoc tuning.  Thresholds are guesses."""
    mat = {c: sum(VALUES[p.piece_type] for p in b.piece_map().values() if p.color == c and p.piece_type in VALUES)
           for c in (chess.WHITE, chess.BLACK)}
    stacked = 0
    for c in (chess.WHITE, chess.BLACK):
        for f in range(8):
            n = sum(1 for sq in b.pieces(chess.PAWN, c) if chess.square_file(sq) == f)
            stacked = max(stacked, n)
    n_pieces = len(b.piece_map())
    imb = mat[chess.WHITE] - mat[chess.BLACK]
    flags = []
    if abs(imb) > 6:
        flags.append("material_imbalance_gt_6")
    if n_pieces > 20:
        flags.append("more_than_20_pieces")
    if stacked >= 3:
        flags.append("three_pawns_on_one_file")
    if len(b.pieces(chess.QUEEN, chess.WHITE)) + len(b.pieces(chess.QUEEN, chess.BLACK)) > 2:
        flags.append("extra_queens")
    return {"material_white": mat[chess.WHITE], "material_black": mat[chess.BLACK], "imbalance": imb,
            "pieces": n_pieces, "decoration_pieces": n_pieces - len(skel), "max_pawns_on_a_file": stacked,
            "flags": flags, "used_as_filter": False}

def cmd_finalize(a) -> int:
    """Re-judge every raw survivor in full (non-fast, default budget) mode, dedupe under symmetry, write files."""
    seeds = load_seeds(Path(a.canonical))
    skel = {chess.parse_square(s) for s in seeds[0]["skeleton"].squares}
    first, familiar = seeds[0]["first"], seeds[0]["familiar"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seen = {pos_key(chess.Board(s["fen"])): s["id"] for s in seeds}
    versions = {"composer_py_sha256_lf": lf_sha(Path(__file__)),
                "composer_py_sha256_lf_at_search_time": a.search_composer_sha or "not recorded",
                "oracle_py_sha256_lf": lf_sha(HERE / "oracle.py"),
                "composer_skeleton_py_sha256_lf": lf_sha(HERE / "composer_skeleton.py"),
                "python": platform.python_version(), "python_chess": chess.__version__}
    index, rejected = [], []
    base_caps = len(standard_san(seeds[0]["fen"], familiar)[1])     # captures in the corpus line itself
    for rawf in a.raw:
        raw = json.loads(Path(rawf).read_text(encoding="utf-8"))
        for s in raw["survivors"]:
            b = chess.Board(s["fen"])
            k = pos_key(b)
            if k in seen:
                rejected.append((s["name"], "duplicate of " + seen[k]))
                continue
            # the search used SAN without capture marks (python-chess parses it leniently); store standard SAN
            first_c, = standard_san(s["fen"], [first])[0]
            fam_c, caps = standard_san(s["fen"], familiar)
            v = judge_board(b, first_c, fam_c, s["name"], fast=False, budget=oracle.DEFAULT_BUDGET)
            if v.status != oracle.PASS:
                rejected.append((s["name"], f"full re-verification {v.status} {v.codes}"))
                continue
            seen[k] = s["name"]
            fid = f"E-{s['name']}"
            rec = {
                "id": fid, "fen": s["fen"], "orientation": "canonical (white attacks, skeleton in b-file corner)",
                "decoration": sorted(f"{p}@{sq}" for sq, p in decoration_set(b, skel)),
                "authenticity": authenticity(b, skel),
                "first_move": first_c, "declared": DECLARED, "lines": {"familiar": fam_c},
                "lines_as_searched": {"first_move": first, "familiar": familiar},
                "familiar_line_captures": caps, "extra_line_captures_vs_corpus": len(caps) - base_caps,
                "images": {t: sk.transform_fen(s["fen"], t) for t in sk.TRANSFORMS},
                "symmetry_key": k,
                "provenance": {"mode": raw["mode"], "seed": raw["seed"], "iteration": s["iteration"],
                               "layer_history": s["lineage"], "nearest_corpus": s["nearest_corpus"],
                               "distance_from_nearest_corpus_decoration": s["distance"]},
                "oracle": {"status": v.status, "codes": v.codes, "nodes": v.nodes, "tier": v.evidence_tier,
                           "mode": "full (not fast)", "python_only": True, "meta": v.meta},
                "versions": versions,
                "engine_certified": False,
                "note": "Python oracle PASS only. Run `composer.py verify` with Stockfish to upgrade the tier. "
                        "Not shown to catch human players.",
            }
            (out / f"{fid}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
            index.append({"id": fid, "fen": s["fen"], "distance": s["distance"], "nearest_corpus": s["nearest_corpus"],
                          "mode": raw["mode"], "seed": raw["seed"]})
    (out / "index.json").write_text(json.dumps({"composer_version": VERSION, "versions": versions, "survivors": index,
                                                "rejected_at_finalize": rejected}, indent=1), encoding="utf-8")
    print(f"finalized {len(index)} survivors into {out}/ ; rejected at finalize: {len(rejected)}")
    for r in rejected:
        print("  rejected", r)
    return 0


# ------------------------------------------------------------------- verify

def cmd_verify(a) -> int:
    """Re-judge every composed/*.json with the engine cross-checks (run this on a machine with Stockfish)."""
    d = Path(a.dir)
    files = sorted(p for p in d.glob("E-*.json"))
    eng, info = oracle.open_engine(a.engine)
    bad = 0
    try:
        for f in files:
            rec = json.loads(f.read_text(encoding="utf-8"))
            cand = oracle.Candidate(rec["id"], rec["fen"], rec["first_move"], rec["declared"], rec["lines"])
            v = oracle.judge(cand, engine=eng, depth=a.depth, engine_info=info)
            ok = v.status == oracle.PASS and v.evidence_tier == "two-engine"
            bad += not ok
            print(f"{'ok  ' if ok else 'WRONG'} {rec['id']:12} -> {v.status:7} codes={v.codes} nodes={v.nodes} tier={v.evidence_tier}")
            for ch in v.checks:
                if not ch.ok or a.verbose:
                    print(f"        {'PASS' if ch.ok else 'FAIL'} {ch.name}  {ch.detail}")
    finally:
        eng.quit()
    print(f"\n{'ALL SURVIVORS TWO-ENGINE PASS' if not bad else str(bad) + ' SURVIVOR(S) NOT CERTIFIED'} ({len(files)} checked)")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canonical", default=str(HERE / "positions" / "canonical.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--mode", choices=["guided", "unguided"], required=True)
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--evals", type=int, default=400)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_search)
    f = sub.add_parser("finalize")
    f.add_argument("--raw", nargs="+", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--search-composer-sha", default=None,
                   help="LF-normalised SHA-256 of the composer.py that ran the search, if it differs from this file")
    f.set_defaults(fn=cmd_finalize)
    v = sub.add_parser("verify")
    v.add_argument("dir")
    v.add_argument("--engine", required=True)
    v.add_argument("--depth", type=int, default=24)
    v.add_argument("--verbose", action="store_true")
    v.set_defaults(fn=cmd_verify)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
