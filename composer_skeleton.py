#!/usr/bin/env python3
"""Skeleton loader for the Einstellung composer (v0.1).

A *skeleton* is the structural core of a familiar (longer) mating line: the
pieces that line moves or captures, both kings, and the defender's unmoved
pieces that stand next to the defender's king in the final mating position
(the blockers that make a smothered mate smothered).  Everything else on the
board is *decoration*: the composer's job is to add decoration that creates a
shorter mate sharing the first move, then hand the result to oracle.py.

What a skeleton is NOT: it is a structural extraction, not a proof that each
piece is necessary.  Necessity is what the gate's falsification controls
test.  The loader reports two measured properties instead of assuming them:
``replays`` (the familiar line is still legal on the bare skeleton) and
``self_mates`` (it still ends in checkmate there).

Symmetry group: mirror the files (a<->h) and/or swap the colours (flip the
ranks, swap the sides, swap who is to move).  Chess rules are invariant under
both when there are no castling rights and no en-passant square, which is
what oracle.py assumes of its candidates.  Four transforms, so each skeleton
has up to four images; the canonical key is the smallest image, so a
Black-attacking position and its White-attacking twin share one key.

Usage:
    python composer_skeleton.py list
    python composer_skeleton.py export skeletons.json
    python composer_skeleton.py selftest          # runs oracle.py, python-only
"""
# SPDX-License-Identifier: GPL-3.0-or-later  (repo LICENSE is the GPL-3.0 text)
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess

HERE = Path(__file__).resolve().parent
VERSION = "0.1"

# ---------------------------------------------------------------- transforms

TRANSFORMS = ("id", "H", "C", "HC")  # H = mirror files, C = colour swap


def _sq(sq: int, t: str) -> int:
    f, r = chess.square_file(sq), chess.square_rank(sq)
    if "H" in t:
        f = 7 - f
    if "C" in t:
        r = 7 - r
    return chess.square(f, r)


def transform_board(b: chess.Board, t: str) -> chess.Board:
    """Image of ``b`` under ``t``.  Castling rights and en passant are dropped."""
    out = chess.Board(None)
    for sq, p in b.piece_map().items():
        colour = (not p.color) if "C" in t else p.color
        out.set_piece_at(_sq(sq, t), chess.Piece(p.piece_type, colour))
    out.turn = (not b.turn) if "C" in t else b.turn
    return out


def transform_move(m: chess.Move, t: str) -> chess.Move:
    return chess.Move(_sq(m.from_square, t), _sq(m.to_square, t), m.promotion)


def transform_san_line(fen: str, sans: List[str], t: str) -> List[str]:
    """Replay ``sans`` from ``fen`` and re-express the line on the transformed board."""
    b = chess.Board(fen)
    tb = transform_board(b, t)
    out = []
    for s in sans:
        mv = b.parse_san(s)
        tm = transform_move(mv, t)
        out.append(tb.san(tm))
        b.push(mv)
        tb.push(tm)
    return out


def transform_fen(fen: str, t: str) -> str:
    return transform_board(chess.Board(fen), t).fen()


# ------------------------------------------------------------------ skeleton

@dataclass
class Skeleton:
    source_id: str
    source_fen: str
    attacker: bool                      # chess.WHITE / chess.BLACK
    familiar_san: List[str]
    squares: List[str]                  # skeleton squares (names) on the source board
    roles: Dict[str, str]               # square name -> why it is in the skeleton
    frame_fen: str                      # bare board containing only skeleton pieces
    decoration: List[str]               # the other occupied squares on the source board
    replays: bool                       # familiar line legal on the bare frame
    self_mates: bool                    # ... and ends in checkmate there
    canonical_key: str = ""
    canonical_transform: str = ""       # transform that maps this frame onto the key
    warnings: List[str] = field(default_factory=list)


def extract(source_id: str, fen: str, familiar_san: List[str]) -> Skeleton:
    b = chess.Board(fen)
    start = b.copy()
    attacker = b.turn
    origin: Dict[int, int] = {sq: sq for sq in b.piece_map()}   # current square -> start square
    roles: Dict[int, str] = {}
    for colour in (chess.WHITE, chess.BLACK):
        k = b.king(colour)
        roles[k] = "king"
    warnings: List[str] = []
    for san in familiar_san:
        mv = b.parse_san(san)
        o = origin.pop(mv.from_square)
        pc = start.piece_at(o)
        roles.setdefault(o, "mover")
        if b.is_castling(mv):
            warnings.append("castling in familiar line: the rook's move is not tracked, frame will be wrong")
        if b.is_en_passant(mv):
            warnings.append("en passant in familiar line: captured pawn not tracked")
        if mv.to_square in origin:
            cap = origin.pop(mv.to_square)
            roles.setdefault(cap, "captured")
        origin[mv.to_square] = o
        b.push(mv)
    if not b.is_checkmate():
        warnings.append("familiar line does not end in checkmate on the source board")
    defender = not attacker
    dk = b.king(defender)
    for sq in chess.SquareSet(chess.BB_KING_ATTACKS[dk]):
        p = b.piece_at(sq)
        if p and p.color == defender and sq in origin:
            roles.setdefault(origin[sq], "blocker")
    frame = chess.Board(None)
    for sq in roles:
        frame.set_piece_at(sq, start.piece_at(sq))
    frame.turn = attacker
    # measured properties of the bare frame
    replays, self_mates = True, False
    try:
        t = frame.copy()
        for san in familiar_san:
            t.push(t.parse_san(san))
        self_mates = t.is_checkmate()
    except Exception:
        replays = False
    squares = sorted(roles, key=lambda s: (chess.square_rank(s), chess.square_file(s)))
    deco = [chess.square_name(s) for s in start.piece_map() if s not in roles]
    sk = Skeleton(
        source_id=source_id, source_fen=fen, attacker=attacker, familiar_san=list(familiar_san),
        squares=[chess.square_name(s) for s in squares],
        roles={chess.square_name(s): roles[s] for s in squares},
        frame_fen=frame.fen(), decoration=sorted(deco),
        replays=replays, self_mates=self_mates, warnings=warnings,
    )
    sk.canonical_key, sk.canonical_transform = canonical(frame)
    return sk


def _key(b: chess.Board) -> str:
    return f"{b.board_fen()} {'w' if b.turn else 'b'}"


def canonical(frame: chess.Board) -> Tuple[str, str]:
    """Smallest image of the frame under the four transforms (ties keep the first)."""
    best: Optional[Tuple[str, str]] = None
    for t in TRANSFORMS:
        k = _key(transform_board(frame, t))
        if best is None or k < best[0]:
            best = (k, t)
    return best  # type: ignore[return-value]


# ------------------------------------------------------------------- loading

def load_skeletons(canonical_json: Path, statuses=("verified", "verified_puzzle_only")) -> List[Skeleton]:
    raw = json.loads(canonical_json.read_text(encoding="utf-8"))
    out = []
    for p in raw["positions"]:
        if p["status"] not in statuses:
            continue
        fam = p["lines"].get("familiar", {}).get("san")
        if not fam:
            print(f"WARNING: {p['id']} skipped: no familiar-line SAN recorded", file=sys.stderr)
            continue
        out.append(extract(p["id"], p["fen"], fam))
    return out


def families(sks: List[Skeleton]) -> Dict[str, List[Skeleton]]:
    fam: Dict[str, List[Skeleton]] = {}
    for s in sks:
        fam.setdefault(s.canonical_key, []).append(s)
    return fam


# ----------------------------------------------------------------------- CLI

def _show(sk: Skeleton) -> str:
    return (f"{sk.source_id:3} attacker={'W' if sk.attacker else 'B'} "
            f"pieces={len(sk.squares)} decoration={len(sk.decoration)} "
            f"replays={sk.replays} self_mates={sk.self_mates}")


def cmd_list(a) -> int:
    sks = load_skeletons(Path(a.canonical))
    for s in sks:
        print(_show(s))
        print("    frame:", s.frame_fen)
        print("    roles:", ", ".join(f"{k}:{v}" for k, v in s.roles.items()))
        for w in s.warnings:
            print("    WARNING:", w)
    print()
    for i, (key, members) in enumerate(families(sks).items(), 1):
        print(f"family {i}: key {key}")
        print("    members:", ", ".join(f"{m.source_id}({m.canonical_transform})" for m in members))
    return 0


def cmd_export(a) -> int:
    sks = load_skeletons(Path(a.canonical))
    fam = families(sks)
    doc = {
        "loader_version": VERSION,
        "transforms": list(TRANSFORMS),
        "note": "Structural skeletons; necessity is not claimed, see replays/self_mates.",
        "families": [
            {"key": k, "members": [s.source_id for s in v]} for k, v in fam.items()
        ],
        "skeletons": [s.__dict__ for s in sks],
    }
    Path(a.out).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {a.out}: {len(sks)} skeletons in {len(fam)} families")
    return 0


def cmd_selftest(a) -> int:
    """Transform invariance: every corpus candidate, under all four transforms, must get
    the same oracle status and reject codes as the untransformed one (python-only)."""
    import oracle  # same folder
    bad = 0

    # 1. board/move round trip
    for fen in ("3r2k1/pp4pp/8/6N1/1b1B4/8/PP2QPPP/R4K1R w - - 0 1",
                "r4k1r/pp2qppp/1p3n2/RB1b4/6n1/P7/1BP3PP/R2R2K1 b - - 0 1"):
        for t in TRANSFORMS:
            b = transform_board(chess.Board(fen), t)
            back = transform_board(b, t)   # every transform is an involution
            ok = back.board_fen() == chess.Board(fen).board_fen() and back.turn == chess.Board(fen).turn
            bad += not ok
            print(f"{'ok  ' if ok else 'WRONG'} involution {t:2} {fen.split()[0][:24]}")

    # 2. skeleton families
    sks = load_skeletons(Path(a.canonical))
    raw = json.loads(Path(a.canonical).read_text(encoding="utf-8"))
    eligible = [p["id"] for p in raw["positions"] if p["status"] in ("verified", "verified_puzzle_only")]
    missing = sorted(set(eligible) - {s.source_id for s in sks})
    bad += bool(missing)
    print(f"{'ok  ' if not missing else 'WRONG'} every eligible position has a skeleton"
          + (f" (missing: {missing})" if missing else f" ({len(eligible)})"))
    for s in sks:
        ok = s.replays and not s.warnings
        bad += not ok
        print(f"{'ok  ' if ok else 'WRONG'} skeleton {_show(s)}")
    fam = families(sks)
    print(f"     {len(sks)} skeletons -> {len(fam)} families")

    # 3. oracle invariance
    for cand, expect in oracle.load_candidates(Path(a.canonical), Path(a.rejects)):
        base = oracle.judge(cand, budget=a.budget)
        for t in TRANSFORMS[1:]:
            try:
                tc = oracle.Candidate(
                    cand.id + "/" + t, transform_fen(cand.fen, t),
                    transform_san_line(cand.fen, [cand.first_move], t)[0],
                    dict(cand.declared),
                    {k: transform_san_line(cand.fen, v, t) for k, v in cand.lines.items()})
                v = oracle.judge(tc, budget=a.budget)
            except Exception as e:  # a transform that cannot even be expressed is a failure
                bad += 1
                print(f"WRONG {cand.id:3} {t:2} transform failed: {e!r}")
                continue
            ok = v.status == base.status and sorted(v.codes) == sorted(base.codes)
            bad += not ok
            print(f"{'ok  ' if ok else 'WRONG'} oracle {cand.id:3} {t:2} {v.status:7} codes={v.codes}"
                  f"  (identity: {base.status} {base.codes}; nodes {base.nodes} -> {v.nodes})")
    print(f"\n{'ALL SKELETON TESTS PASSED' if not bad else str(bad) + ' TEST(S) WRONG'}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canonical", default=str(HERE / "positions" / "canonical.json"))
    ap.add_argument("--rejects", default=str(HERE / "fixtures" / "rejects.json"))
    ap.add_argument("--budget", type=int, default=5_000_000)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    e = sub.add_parser("export")
    e.add_argument("out")
    e.set_defaults(fn=cmd_export)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())