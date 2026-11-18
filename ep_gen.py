
#!/usr/bin/env python3
r"""ep_gen.py v0.4 -- Definition-driven Einstellung generator (Path B, WEAK FORM).

v0.4 over v0.3:
  1. WEAK-FORM PROBE. Entry = mating-optimal move (pattern trigger); the
     tempting FORK is surveyed one move deeper -- after entry and the
     defender's best (longest-resisting) reply. v0.3 surveyed at the ROOT
     and skipped the best move, so every accept was strong-form and died
     on the oracle's alt_first_move_mates uniqueness doctrine.
  2. ORACLE DOCTRINE PRE-CHECK. Alt root moves mating within declared
     short are rejected AT THE GENERATOR, logging alt_total -- equal-speed
     alts are TWIN-ORE for the future Option B lane. Survey is checks-only;
     the oracle still owns the zugzwang edge case at certification.
  3. REALIZED DECLARATIONS. Round 1 proved depth-18 mate distances on
     long mates overshoot (60/81 declared/line mismatches). familiar is
     declared from the replayed line ((plies+1)//2). Probe estimates are
     demoted to provenance.m_familiar_est, labeled hints. Realized-gap
     shortfall is a hard reject.
  4. --short-max ENFORCED (v0.3 declared it, never checked).
  5. ENTRY-MUST-CHECK DOCTRINE GATE. Quiet optimal entries rejected as
     no_check_entry unless --allow-quiet-entry waives it.
  6. Robustness: defender-reply recovery returns None -> record rejected
     as familiar_line_incomplete instead of killing the scan; argument
     sanity enforced at startup.

Record contract (corpus-compatible):
  first_move        = SAN of the ENTRY move (opens the familiar line).
  declared.short    = engine mate distance of the entry.
  declared.familiar = REALIZED length of the replayed familiar line.
  lines.familiar    = entry, defender reply, fork, best play to mate.

Usage:
  python ep_gen.py --check-seeds --seeds-file seeds.json
  python ep_gen.py --seeds-file seeds.json --evals 400 --out ep_scan_r2
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chess
    import chess.engine
except ImportError:
    raise SystemExit("requires python-chess: pip install chess")

VERSION = "0.4"
DEFAULT_ENGINE = (r"C:/Users/44777/Downloads/"
                  r"stockfish-windows-x86-64-universal/stockfish/"
                  r"stockfish-windows-x86-64-universal.exe")

QUEEN = chess.QUEEN

BUILTIN_SEEDS: List[Dict[str, str]] = [
    {"name": "rooklad-1", "note": "two-rook ladder vs cornered king",
     "fen": "7k/8/8/8/8/8/R7/1R4K1 w - - 0 1"},
    {"name": "bishop-1", "note": "bishop net with rook cut-off attempt",
     "fen": "8/8/8/8/8/2B5/1R6/k1K5 w - - 0 1"},
]

REJECT_CODES = (
    "probe_failed", "no_fast_mate", "mate_too_trivial", "short_too_long",
    "no_check_entry", "queen_led_best", "corner_signature",
    "alt_first_move_mates", "probe_drift", "no_prolonging_check",
    "realized_gap_shortfall", "duplicate", "familiar_line_incomplete",
    "probe_error", "invalid_seed_fen",
)

# ------------------------------------------------------------- helpers ------

def placement(fen: str) -> Optional[str]:
    parts = fen.split()
    if len(parts) < 2 or parts[1] not in ("w", "b"):
        return None
    return " ".join(parts[:2])

def canonical_form(board: chess.Board) -> str:
    forms = [board.board_fen()]
    for fn in (chess.flip_vertical, chess.flip_horizontal):
        try:
            b2 = board.copy(stack=False)
            b2.apply_transform(fn)
            forms.append(b2.board_fen())
        except Exception:
            pass
    return min(forms)

# ------------------------------------------------------------- engine I/O --

class Engine:
    def __init__(self, path: str, probe_depth: int):
        self.path = path
        self.depth = probe_depth
        self.eng: Optional[chess.engine.SimpleEngine] = None
        self._restarts = 0

    def get(self) -> chess.engine.SimpleEngine:
        if self.eng is None:
            self.eng = chess.engine.SimpleEngine.popen_uci(self.path)
        return self.eng

    def analyse(self, board: chess.Board,
                pov_color: Optional[chess.Color] = None):
        if pov_color is None:
            pov_color = board.turn
        for attempt in range(2):
            try:
                info = self.get().analyse(
                    board, chess.engine.Limit(depth=self.depth),
                    info=chess.engine.INFO_ALL)
                if "score" not in info:
                    return None, None, []
                mate = info["score"].pov(pov_color).mate()
                pv = info.get("pv") or []
                best = pv[0] if pv else None
                return mate, best, pv
            except chess.engine.EngineTerminatedError:
                if self._restarts >= 3:
                    raise
                self._restarts += 1
                print(f"  [engine died; restart {self._restarts}/3]")
                self.close()
            except Exception:
                if attempt:
                    raise
        return None, None, []

    def close(self):
        if self.eng is not None:
            try:
                self.eng.quit()
            except Exception:
                try:
                    self.eng.kill()
                except Exception:
                    pass
            self.eng = None

# ------------------------------------------------------------ core probing --

def tempting_checks(board: chess.Board, ban_queen: bool) -> List[chess.Move]:
    out = []
    for mv in board.legal_moves:
        if board.gives_check(mv):
            if ban_queen and board.piece_type_at(mv.from_square) == QUEEN:
                continue
            out.append(mv)
    return out

def corner_smothered(board: chess.Board) -> bool:
    k = board.king(not board.turn)
    if k is None:
        return False
    x, y = chess.square_file(k), chess.square_rank(k)
    if x not in (0, 7) or y not in (0, 7):
        return False
    dx = 1 if x == 0 else -1
    if y == 0:
        shields = [(dx, 0), (dx, 1), (0, 1)]
    else:
        shields = [(dx, 0), (dx, -1), (0, -1)]
    for ddx, ddy in shields:
        fx, fy = x + ddx, y + ddy
        if not (0 <= fx < 8 and 0 <= fy < 8):
            continue
        pc = board.piece_at(chess.square(fx, fy))
        if pc is None or pc.color == board.turn:
            return False
    return True

def probe_candidate(board: chess.Board, eng: Engine,
                    args) -> Dict[str, Any]:
    """WEAK-FORM qualification probe (attacker to move at entry).
    All mate values are attacker-POV (positive = attacker mates)."""
    res: Dict[str, Any] = {"verdict": "reject:unknown"}
    attacker = board.turn

    m_best, best_move, _pv = eng.analyse(board, pov_color=attacker)
    if best_move is None:
        return {**res, "verdict": "reject:probe_failed"}
    if m_best is None or m_best <= 0:
        return {**res, "verdict": "reject:no_fast_mate",
                "best_move": board.san(best_move)}
    if m_best < args.short_min:
        return {**res, "verdict": "reject:mate_too_trivial",
                "m_best": m_best, "best_move": board.san(best_move)}
    if m_best > args.short_max:
        return {**res, "verdict": "reject:short_too_long",
                "m_best": m_best, "best_move": board.san(best_move)}
    entry_san = board.san(best_move)

    # doctrine gate: the entry is the pattern TRIGGER -- a check
    if not board.gives_check(best_move) and not args.allow_quiet_entry:
        return {**res, "verdict": "reject:no_check_entry",
                "m_best": m_best, "best_move": entry_san}

    if args.ban_queen_best and \
            board.piece_type_at(best_move.from_square) == QUEEN:
        return {**res, "verdict": "reject:queen_led_best",
                "m_best": m_best, "best_move": entry_san}

    if corner_smothered(board):
        if board.piece_type_at(best_move.from_square) != chess.KNIGHT:
            return {**res, "verdict": "reject:corner_signature",
                    "m_best": m_best, "best_move": entry_san}

    # --- uniqueness pre-check (oracle doctrine, twin-ore logging) -------
    for mv in board.legal_moves:
        if mv == best_move or not board.gives_check(mv):
            continue
        board.push(mv)
        if board.is_checkmate():
            m_alt = 0
        else:
            m_alt, _, _ = eng.analyse(board, pov_color=attacker)
        board.pop()
        if m_alt is not None and m_alt >= 0 and (m_alt + 1) <= m_best:
            return {**res, "verdict": "reject:alt_first_move_mates",
                    "m_best": m_best, "best_move": entry_san,
                    "alt_move": board.san(mv), "alt_total": m_alt + 1}

    # --- weak form: entry = best move; fork surveyed one move deeper ----
    entry = best_move
    board.push(entry)
    m_after_entry, reply, _pv2 = eng.analyse(board, pov_color=attacker)
    if reply is None:
        board.pop()
        return {**res, "verdict": "reject:probe_failed"}
    if m_after_entry is None or m_after_entry <= 0:
        board.pop()
        return {**res, "verdict": "reject:no_fast_mate",
                "m_best": m_best, "best_move": entry_san}
    if m_after_entry != m_best - 1:
        board.pop()
        return {**res, "verdict": "reject:probe_drift",
                "m_best": m_best, "m_seen": m_after_entry,
                "best_move": entry_san}
    reply_san = board.san(reply)
    board.push(reply)

    m_node, best2, _pv3 = eng.analyse(board, pov_color=attacker)
    if best2 is None or m_node is None or m_node <= 0:
        board.pop(); board.pop()
        return {**res, "verdict": "reject:probe_failed",
                "m_best": m_best, "best_move": entry_san}
    if m_node != m_best - 1:
        board.pop(); board.pop()
        return {**res, "verdict": "reject:probe_drift",
                "m_best": m_best, "m_seen": m_node, "best_move": entry_san}

    verdict_probe = None
    tried = 0
    for mv in tempting_checks(board, ban_queen=args.ban_queen_tempting):
        if mv == best2:
            continue
        tried += 1
        board.push(mv)
        if board.is_checkmate():
            m_after = 0
        else:
            m_after, _, _ = eng.analyse(board, pov_color=attacker)
        board.pop()
        if m_after is None or m_after <= 0:
            continue
        if m_after - m_node >= args.gap:
            verdict_probe = {
                "verdict": "ACCEPT", "m_best": m_best,
                "best_move": entry_san, "best_move_uci": entry.uci(),
                "defender_reply": reply_san, "m_node": m_node,
                "fork_move": board.san(mv), "fork_uci": mv.uci(),
                "m_familiar_est": m_after + 2,
                "checks_tried": tried}
            break
    board.pop()
    board.pop()
    if verdict_probe is not None:
        return verdict_probe
    return {**res, "verdict": "reject:no_prolonging_check",
            "m_best": m_best, "best_move": entry_san, "checks_tried": tried}

def build_weak_familiar_line(board: chess.Board, eng: Engine,
                             entry_uci: str, reply_uci: str,
                             fork_uci: str,
                             max_plies: int = 80) -> List[str]:
    """Entry, defender's stored reply, fork, then best play to mate."""
    b = board.copy(stack=False)
    fam: List[str] = []
    try:
        e = chess.Move.from_uci(entry_uci)
        if not b.is_legal(e):
            return []
        fam.append(b.san(e)); b.push(e)
        r = chess.Move.from_uci(reply_uci)
        if not b.is_legal(r):
            return []
        fam.append(b.san(r)); b.push(r)
        f = chess.Move.from_uci(fork_uci)
        if not b.is_legal(f):
            return []
        fam.append(b.san(f)); b.push(f)
    except ValueError:
        return []
    guard = 0
    while not b.is_checkmate():
        if guard >= max_plies or b.is_game_over():
            return []
        guard += 1
        _, best, _pv = eng.analyse(b)
        if best is None or not b.is_legal(best):
            return []
        fam.append(b.san(best))
        b.push(best)
    return fam

def _reply_uci_of(board: chess.Board,
                 probe: Dict[str, Any]) -> Optional[str]:
    """Recover the defender reply's UCI from its recorded SAN.
    Returns None (record gets rejected) instead of raising -- a scan
    must never die because one position could not be reconstructed."""
    b = board.copy(stack=False)
    try:
        b.push(chess.Move.from_uci(probe["best_move_uci"]))
    except ValueError:
        return None
    for mv in b.legal_moves:
        if b.san(mv) == probe["defender_reply"]:
            return mv.uci()
    return None

# ---------------------------------------------------------------- mutation --

def mutate(board: chess.Board, rng: random.Random) -> Optional[chess.Board]:
    b = board.copy(stack=False)
    op = rng.random()
    if op < 0.45:
        movers = [sq for sq in chess.SQUARES
                  if b.piece_at(sq) is not None
                  and b.piece_type_at(sq) != chess.KING]
        empties = [sq for sq in chess.SQUARES if b.piece_at(sq) is None]
        if not movers or not empties:
            return None
        frm = rng.choice(movers)
        piece = b.piece_at(frm)
        b.remove_piece_at(frm)
        b.set_piece_at(rng.choice(empties), piece)
    elif op < 0.80:
        empties = [sq for sq in chess.SQUARES
                   if b.piece_at(sq) is None
                   and chess.square_distance(sq, b.king(chess.BLACK)) <= 4]
        if not empties:
            return None
        ptype = rng.choice([chess.PAWN, chess.KNIGHT, chess.BISHOP,
                            chess.ROOK])
        b.set_piece_at(rng.choice(empties), chess.Piece(ptype, chess.WHITE))
    else:
        targets = [sq for sq in chess.SQUARES
                   if b.piece_at(sq) is not None
                   and b.piece_at(sq).color == chess.BLACK
                   and b.piece_type_at(sq) != chess.KING]
        if not targets:
            return None
        b.remove_piece_at(rng.choice(targets))
    b.castling_rights = chess.BB_EMPTY
    b.ep_square = None
    b.halfmove_clock = 0
    if b.status() != chess.STATUS_VALID:
        return None
    return b

# ------------------------------------------------------------------ output --

def write_jsonl_atomic(path: Path, rows: List[Dict[str, Any]]) -> None:
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, path)

def write_record_atomic(path: Path, doc: Dict[str, Any]) -> None:
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

# -------------------------------------------------------------------- modes --

def check_seeds(args, eng: Engine) -> int:
    seeds = BUILTIN_SEEDS
    if args.seeds_file:
        seeds = json.loads(Path(args.seeds_file).read_text(
            encoding="utf-8-sig"))
    alive = 0
    print(f"grading {len(seeds)} seed(s) at depth {args.depth}:\n")
    for s in seeds:
        try:
            board = chess.Board(s["fen"])
        except ValueError as exc:
            print(f"  {s['name']}: INVALID FEN ({exc})")
            continue
        t0 = time.time()
        try:
            probe = probe_candidate(board, eng, args)
        except Exception as exc:
            print(f"  {s['name']}: PROBE ERROR ({exc!r})")
            continue
        dt = time.time() - t0
        tag = probe["verdict"]
        extra = ""
        if "m_best" in probe:
            extra += (f" best mate in {probe['m_best']} via "
                      f"{probe['best_move']}")
        if tag.startswith("reject:") and "alt_move" in probe:
            extra += (f" | alt root: {probe['alt_move']} (total "
                      f"{probe.get('alt_total', '?')})")
        if tag == "ACCEPT":
            extra += (f" | fork {probe['fork_move']} after "
                      f"{probe['defender_reply']} -> familiar ~"
                      f"{probe['m_familiar_est']} (est)")
            alive += 1
        print(f"  {s['name']:16} [{dt:5.1f}s] {tag}{extra}")
        print(f"      note: {s.get('note', '')}")
    print(f"\n{alive}/{len(seeds)} seeds qualify as-is under the WEAK form.")
    return 0

def run_scan(args, eng: Engine) -> int:
    seeds = BUILTIN_SEEDS
    if args.seeds_file:
        seeds = json.loads(Path(args.seeds_file).read_text(
            encoding="utf-8-sig"))
    if not seeds:
        print("no seeds to scan")
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.rng_seed)

    accepts: List[Dict[str, Any]] = []
    rejects: List[Dict[str, Any]] = []
    seen_canonical: set = set()
    t0 = time.time()

    def flush_partial(reason: str) -> None:
        index_doc = {"generator": "ep_gen", "version": VERSION,
                     "paradigm": "weak-form-shadow",
                     "interrupted": reason != "complete",
                     "records": [a.get("id", a.get("seed", "?"))
                                 for a in accepts]}
        write_record_atomic(out / "scan_index.json", index_doc)
        write_jsonl_atomic(out / "rejects.jsonl", rejects)

    n_errors = 0
    try:
        for s_i, seed in enumerate(seeds):
            try:
                base = chess.Board(seed["fen"])
            except ValueError:
                rejects.append({"seed": seed.get("name"),
                                "code": "invalid_seed_fen"})
                continue
            pool = [(base, 0)]
            try:
                base_probe = probe_candidate(base, eng, args)
            except Exception as exc:
                print(f"  [seed {seed['name']} probe error: {exc!r}]")
                base_probe = {"verdict": "reject:probe_error"}
            if base_probe["verdict"] == "ACCEPT":
                seen_canonical.add(canonical_form(base))
                print(f"  [seed {seed['name']} itself qualifies]")
            per_seed = args.evals // len(seeds) + 1
            for ev in range(1, per_seed + 1):
                if not pool:
                    break
                parent, depth_mut = pool[rng.randrange(len(pool))]
                child = mutate(parent, rng)
                if child is None:
                    continue
                if canonical_form(child) in seen_canonical:
                    rejects.append({"seed": seed["name"],
                                    "code": "duplicate"})
                else:
                    try:
                        probe = probe_candidate(child, eng, args)
                    except Exception as exc:
                        n_errors += 1
                        probe = {"verdict": "reject:probe_error"}
                        rejects.append({"seed": seed["name"],
                                        "code": "probe_error",
                                        "detail": repr(exc)})
                    if probe["verdict"] == "ACCEPT":
                        reply_uci = _reply_uci_of(child, probe)
                        if reply_uci is None:
                            fam = []
                        else:
                            fam = build_weak_familiar_line(
                                child, eng, probe["best_move_uci"],
                                reply_uci, probe["fork_uci"])
                        if not fam:
                            rejects.append({"seed": seed["name"],
                                            "code":
                                            "familiar_line_incomplete"})
                            probe = {"verdict":
                                     "reject:familiar_line_incomplete"}
                        else:
                            real_fam = (len(fam) + 1) // 2
                            if real_fam - probe["m_best"] < args.gap:
                                rejects.append({
                                    "seed": seed["name"],
                                    "code": "realized_gap_shortfall",
                                    "est": probe["m_familiar_est"],
                                    "realized": real_fam})
                                probe = {"verdict":
                                         "reject:"
                                         "realized_gap_shortfall"}
                            else:
                                rec_id = (f"{args.prefix}-{s_i + 1}-"
                                          f"{ev:03d}")
                                doc = {
                                    "id": rec_id,
                                    "fen": child.fen(),
                                    "first_move": probe["best_move"],
                                    "declared": {
                                        "short": probe["m_best"],
                                        "familiar": real_fam},
                                    "lines": {"familiar": fam},
                                    "symmetry_key": " ".join(
                                        child.fen().split()[:2]),
                                    "provenance": {
                                        "generator": "ep_gen",
                                        "version": VERSION,
                                        "paradigm":
                                            "weak-form-shadow",
                                        "seed_name": seed["name"],
                                        "mutation_depth":
                                            depth_mut + 1,
                                        "note": seed.get("note", ""),
                                        "engine_probe_depth":
                                            args.depth,
                                        "entry_uci":
                                            probe["best_move_uci"],
                                        "defender_reply":
                                            probe["defender_reply"],
                                        "fork": probe["fork_move"],
                                        "fork_uci":
                                            probe["fork_uci"],
                                        "m_familiar_est":
                                            probe["m_familiar_est"],
                                        "est_note": ("depth-18 distance "
                                                     "HINT, not a "
                                                     "declaration"),
                                        "realized_familiar":
                                            real_fam,
                                        "familiar_line_verified_by":
                                            "pv-replay",
                                    },
                                }
                                write_record_atomic(
                                    out / f"{rec_id}.json", doc)
                                seen_canonical.add(
                                    canonical_form(child))
                                accepts.append({
                                    "id": rec_id,
                                    "seed": seed["name"],
                                    **{k: v for k, v in
                                       probe.items()
                                       if k != "verdict"},
                                    "realized_familiar": real_fam,
                                    "fen": child.fen()})
                                print(f"  ACCEPT {rec_id}: short "
                                      f"{probe['m_best']} vs familiar "
                                      f"{real_fam} (est "
                                      f"{probe['m_familiar_est']}) "
                                      f"fork {probe['fork_move']} "
                                      f"after "
                                      f"{probe['defender_reply']}")
                                pool.append((child, depth_mut + 1))
                    else:
                        code = probe["verdict"].split(":", 1)[-1]
                        rejects.append({"seed": seed["name"],
                                        "code": code})
                        pool.append((child, depth_mut + 1))
                if len(pool) > 64:
                    pool.pop(0)
                if ev % 25 == 0:
                    print(f"  ... seed {seed['name']}: {ev}/{per_seed} "
                          f"mutants, {len(accepts)} accept(s), "
                          f"{time.time() - t0:.0f}s elapsed")
                    flush_partial("running")
        flush_partial("complete")
    except KeyboardInterrupt:
        flush_partial("interrupted")
        print(f"\ninterrupted: {len(accepts)} accepted, "
              f"{len(rejects)} rejected so far; partial index + "
              f"reject audit written")
        return 130

    print(f"\ndone: {len(accepts)} accepted, {len(rejects)} rejected, "
          f"{n_errors} probe error(s) in "
          f"{(time.time() - t0) / 60:.1f} min")
    print(f"records + scan_index.json in {out}; rejection audit in "
          f"{out}\\rejects.jsonl")
    return 0

# --------------------------------------------------------------------- main --

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Definition-driven EP generator (weak form)")
    ap.add_argument("--out", default="ep_scan_r2")
    ap.add_argument("--engine", default=DEFAULT_ENGINE)
    ap.add_argument("--depth", type=int, default=18)
    ap.add_argument("--short-max", type=int, default=3)
    ap.add_argument("--short-min", dest="short_min", type=int,
                    default=2)
    ap.add_argument("--gap", type=int, default=2)
    ap.add_argument("--evals", type=int, default=400)
    ap.add_argument("--rng-seed", dest="rng_seed", type=int,
                    default=1)
    ap.add_argument("--prefix", default="E-W")
    ap.add_argument("--check-seeds", action="store_true")
    ap.add_argument("--seeds-file", default=None)
    ap.add_argument("--allow-quiet-entry",
                    dest="allow_quiet_entry", action="store_true",
                    default=False)
    ap.add_argument("--ban-queen-tempting",
                    dest="ban_queen_tempting",
                    action="store_true", default=True)
    ap.add_argument("--allow-queen-tempting",
                    dest="ban_queen_tempting",
                    action="store_false")
    ap.add_argument("--ban-queen-best", dest="ban_queen_best",
                    action="store_true", default=True)
    ap.add_argument("--allow-queen-best", dest="ban_queen_best",
                    action="store_false")
    args = ap.parse_args(argv)

    if args.short_min > args.short_max:
        raise SystemExit(f"--short-min ({args.short_min}) exceeds "
                         f"--short-max ({args.short_max})")
    if args.gap < 1:
        raise SystemExit("--gap must be >= 1")
    if not Path(args.engine).exists():
        raise SystemExit(f"engine not found: {args.engine} "
                         f"(pass --engine)")

    eng = Engine(args.engine, args.depth)
    try:
        if args.check_seeds:
            return check_seeds(args, eng)
        return run_scan(args, eng)
    except KeyboardInterrupt:
        print("\ninterrupted; partial output preserved where applicable")
        return 130
    finally:
        eng.close()

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())