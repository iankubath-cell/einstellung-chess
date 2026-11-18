#!/usr/bin/env python3
r"""fen_eval.py v0.2 -- interactive Einstellung-doctrine FEN evaluator.

Paste ANY text (e.g. raw Base44 output, captions and all): every
well-formed FEN embedded in it is extracted and adjudicated. Missing
fields are auto-completed to 'w - - 0 1' (announced in the output).

Doctrine (unchanged from v0.1, lessons retained):
  * totals <= --horizon (default 3) are PROVEN by exhaustive
    python-chess enumeration; longer totals are engine HINTS, always
    labelled '(eng)' -- round-2 finding: engine mate distances are
    upper bounds, not truth.
  * the root survey covers ALL legal moves, checks AND quiet ones
    (Class-1 lesson: quiet root mates are common in light endgames).
  * verdicts: TWIN-CANDIDATE (Option B ore, oracle rejects by design)
    / SHADOW-ROOT (strong form at the root, archive tier)
    / SINGLE-KEY DECOY (off-paradigm) / DEGENERATE / NO-MATE.

v0.2 review-pass fixes:
  NameError crash in the breaks display (tempting_b/temping_b typo);
  'depth N' command now actually changes search depth;
  engine/dispute conflicts no longer contaminate best/optimal;
  one bad FEN or crash kills only that position, never the session;
  Ctrl+C skips position (batch) / aborts position (interactive);
  FEN extraction from arbitrary pasted text; capped engine restarts.

Usage:
  python -u fen_eval.py              interactive ('help' for commands)
  python -u fen_eval.py fens.txt     batch: raw text file, any format
Options: --depth 18 --horizon 3 --budget 300000 --engine <path>
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import time

try:
    import chess
    import chess.engine
except ImportError:
    raise SystemExit("requires python-chess: pip install chess")

VERSION = "0.2"
def _default_engine() -> str:
    """Single source of truth: pipeline_config.json; hardcoded fallback
    only if the config is unreadable (e.g. run from another folder)."""
    try:
        import json as _json
        cfg = _json.load(open("pipeline_config.json",
                              encoding="utf-8-sig"))
        return cfg["paths"]["stockfish"]
    except Exception:
        return "C:/Users/44777/Downloads/stockfish-windows-x86-64-universal/stockfish/stockfish-windows-x86-64-universal.exe"
DEFAULT_ENGINE = _default_engine()

# ------------------------------------------------- exact mate enumeration --

class BudgetExceeded(Exception):
    pass

class NodeBudget:
    __slots__ = ("left",)
    def __init__(self, n: int):
        self.left = n
    def tick(self):
        self.left -= 1
        if self.left < 0:
            raise BudgetExceeded()

def mate_in_n(b: chess.Board, n: int, bud: NodeBudget) -> bool:
    """Attacker (side to move) forces mate in <= n attacker moves."""
    if n < 1:
        return False
    bud.tick()
    moves = list(b.legal_moves)
    if not moves:
        return False                    # stalemate after our own move
    moves.sort(key=lambda m: not b.gives_check(m))   # checks first
    for mv in moves:
        b.push(mv)
        if b.is_checkmate():
            ok = True
        elif n > 1:
            ok = all_defenses_lose(b, n - 1, bud)
        else:
            ok = False
        b.pop()
        if ok:
            return True
    return False

def all_defenses_lose(b: chess.Board, n: int, bud: NodeBudget) -> bool:
    """Defender (side to move): EVERY reply loses to mate in <= n.
    No legal replies = stalemate = failure (checkmate is impossible
    here: the attacker's mating move ends the line before this call)."""
    bud.tick()
    moves = list(b.legal_moves)
    if not moves:
        return False
    for mv in moves:
        b.push(mv)
        ok = mate_in_n(b, n, bud)
        b.pop()
        if not ok:
            return False
    return True

def remaining_exact(b: chess.Board, bud: NodeBudget,
                    maxk: int):
    """Defender to move. Smallest k in 1..maxk such that every
    defense loses in k; None if none within maxk. Budget-safe."""
    if maxk < 1 or not any(True for _ in b.legal_moves):
        return None
    for k in range(1, maxk + 1):
        if all_defenses_lose(b, k, bud):
            return k
    return None

# -------------------------------------------------------------- engine -----

class Engine:
    def __init__(self, path: str):
        self.path = path
        self.eng = None
        self._restarts = 0

    def get(self):
        if self.eng is None:
            self.eng = chess.engine.SimpleEngine.popen_uci(self.path)
        return self.eng

    def mate(self, board: chess.Board, pov, depth: int):
        """Engine mate hint at the GIVEN depth (v0.2: per-call depth).
        Returns None on any failure after capped retries."""
        for attempt in range(3):
            try:
                info = self.get().analyse(
                    board, chess.engine.Limit(depth=depth),
                    info=chess.engine.INFO_ALL)
                if "score" not in info:
                    return None
                return info["score"].pov(pov).mate()
            except chess.engine.EngineTerminatedError:
                self.eng = None
                self._restarts += 1
                if self._restarts > 6:
                    print("  [engine unavailable; treating as no data]")
                    return None
            except Exception:
                if attempt == 2:
                    return None
        return None

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

# --------------------------------------------------------- FEN extraction --

RANK = r"[pPnNbBrRqQkK12345678]+"
FEN_BOARD_RE = re.compile(RANK + r"(?:/" + RANK + r"){7}")
SIDE_RE = re.compile(r"^[wWbB]$")
CASTLE_RE = re.compile(r"^(-|[KQkqA-Ha-h]{1,4})$")
EP_RE = re.compile(r"^(-|[a-h][1-8])$")
NUM_RE = re.compile(r"^\d+$")
STRIP = "(){}[]<>,.;:!?'\"" + '"' + "\u2014\u2013"

def extract_fens(text: str):
    """Pull every FEN out of arbitrary pasted text.
    Returns a list of (fen_string, auto_completed: bool)."""
    toks = [t.strip(STRIP) for t in text.split()]
    out = []
    i = 0
    while i < len(toks):
        if FEN_BOARD_RE.fullmatch(toks[i]):
            fields = [toks[i]]
            j = i + 1
            auto = True
            if j < len(toks) and SIDE_RE.match(toks[j]):
                fields.append(toks[j].lower()); j += 1; auto = False
                if j < len(toks) and CASTLE_RE.match(toks[j]):
                    fields.append(toks[j]); j += 1
                    if j < len(toks) and EP_RE.match(toks[j]):
                        fields.append(toks[j]); j += 1
                        if (j + 1 < len(toks) and NUM_RE.match(toks[j])
                                and NUM_RE.match(toks[j + 1])):
                            fields.append(toks[j])
                            fields.append(toks[j + 1])
                            j += 2
            pad = {1: ["w", "-", "-", "0", "1"],
                   2: ["-", "-", "0", "1"],
                   3: ["-", "0", "1"],
                   4: ["0", "1"],
                   5: ["1"]}
            if len(fields) < 6:
                fields.extend(pad[len(fields)])
            out.append((" ".join(fields), auto))
            i = j
        else:
            i += 1
    return out

# --------------------------------------------------------------- analysis --

def analyse(fen: str, auto: bool, eng: Engine, depth: int, horizon: int,
            move_budget: int) -> None:
    try:
        b = chess.Board(fen)
    except ValueError as exc:
        print(f"  INVALID FEN: {exc}\n  ({fen})")
        return
    if b.status() != chess.STATUS_VALID:
        print(f"  WARNING: position status {b.status()!r} (proceeding)")
    if auto:
        print("  [fields auto-completed to 'w - - 0 1']")
    attacker = b.turn
    att_name = "White" if attacker else "Black"
    if b.is_check():
        print("  NOTE: side to move is IN CHECK")
    legal = list(b.legal_moves)
    if not legal:
        state = ("checkmate" if b.is_checkmate()
                 else "stalemate or no legal moves")
        print(f"  nothing to evaluate: {state}")
        return
    print(f"\n=== {att_name} to move; {len(legal)} legal moves; "
          f"exact horizon {horizon} (longer totals labelled 'eng')")
    t0 = time.time()

    m_eng = eng.mate(b, attacker, depth)
    if m_eng is None:
        print(f"  engine hint at depth {depth}: no forced mate found")
    elif m_eng > 0:
        print(f"  engine hint at depth {depth}: mate in {m_eng}")
    else:
        print(f"  engine hint at depth {depth}: DEFENDER mates "
              f"in {-m_eng} -- hopeless for the attacker")

    rows, disputes, n_unknown = [], [], 0
    for mv in legal:
        san = b.san(mv)
        chk, cap = b.gives_check(mv), b.is_capture(mv)
        b.push(mv)
        total, prov, eng_claim = None, None, None
        if b.is_checkmate():
            total, prov = 1, True
        else:
            try:
                bud = NodeBudget(move_budget)
                k = remaining_exact(b, bud, horizon - 1)
                if k is not None:
                    total, prov = 1 + k, True
                else:
                    prov = False        # exact: no mate within horizon
            except BudgetExceeded:
                prov = None             # unknown within budget
                n_unknown += 1
        if total is None:
            m_after = eng.mate(b, attacker, depth)
            if m_after is not None and m_after > 0:
                eng_claim = m_after + 1
                if prov is False and eng_claim <= horizon:
                    # engine contradicts an exact proof -- do NOT trust
                    disputes.append((san, chk, cap, eng_claim))
                else:
                    total = eng_claim   # hint beyond/consistent
        b.pop()
        rows.append({"san": san, "chk": chk, "cap": cap,
                     "total": total, "prov": prov})

    dt = time.time() - t0
    mated = [r for r in rows if r["total"] is not None]
    if not mated and not disputes:
        msg = (f"  verdict: NO-MATE (nothing forces mate; horizon "
               f"{horizon} exhaustively checked")
        if n_unknown:
            msg += f"; {n_unknown} root(s) exceeded proof budget"
        print(msg + ")")
        return
    if not mated:
        print(f"  verdict: DISPUTED -- engine claims mate, exact proof "
              f"denies it within horizon {horizon}")
        for san, chk, cap, claim in disputes:
            print(f"    {san}: engine claims total {claim}, "
                  f"exact says no mate <= {horizon}")
        print("  raise --horizon (and --budget) and retry to settle it")
        return

    best = min(r["total"] for r in mated)
    optimal = [r for r in mated if r["total"] == best]
    slower = sorted((r for r in mated if r["total"] > best),
                    key=lambda r: r["total"])
    breaks = [r for r in rows if r["total"] is None]

    if all(r["prov"] for r in optimal):
        proof = "EXACT"
    else:
        proof = "partly engine hints"
    print(f"  shortest mate: {best}  ({proof})")
    if m_eng and m_eng > 0 and m_eng != best:
        print(f"  [root engine hint was {m_eng}]")

    def tag(r):
        parts = []
        if r["chk"]:
            parts.append("check")
        if r["cap"]:
            parts.append("capture")
        if not r["chk"] and not r["cap"]:
            parts.append("QUIET")
        s = "(" + ",".join(parts) + ")"
        if r["prov"] is not True and r["total"] is not None \
                and r["total"] > 1:
            s += " (eng)"
        return s

    print(f"  optimal roots ({len(optimal)}):")
    for r in optimal:
        print(f"    {r['san']:10} {tag(r)}")
    if len(optimal) == 1 and not optimal[0]["chk"]:
        print("    -> QUIET optimal root: a checks-only survey would "
              "have MISSED this (Class-1 blindness)")
    if slower:
        print(f"  still mates, slower ({len(slaller)}) -- "
              if False else
              f"  still mates, slower ({len(slower)}) -- familiar-line "
              f"candidates:")
        for r in slower[:10]:
            print(f"    {r['san']:10} total {r['total']} "
                  f"(+{r['total'] - best}) {tag(r)}")
        if len(slower) > 10:
            print(f"    ... and {len(slower) - 10} more")
    if breaks:
        temp = [r for r in breaks if r["chk"] or r["cap"]]
        print(f"  no forced mate found ({len(breaks)} moves; "
              f"{len(temp)} of them checks/captures -- slow mate "
              f"beyond probe or draw):")
        for r in temp[:10]:
            print(f"    {r['san']:10} (check)" if r["chk"]
                  else f"    {r['san']:10} (capture)")
        if len(temp) > 10:
            print(f"    ... and {len(temp) - 10} more")
    for san, chk, cap, claim in disputes:
        print(f"  !! DISPUTE {san}: engine claims total {claim}, "
              f"exact proves no mate <= {horizon} -- exact wins")

    if best == 1:
        print("  verdict: DEGENERATE (mate in 1; below --short-min "
              "floor)")
    elif len(optimal) >= 2:
        print("  verdict: TWIN-CANDIDATE -- equal-speed roots; Option "
              "B ore; shadow oracle rejects BY DESIGN")
    elif slower:
        print("  verdict: SHADOW-ROOT -- unique fast key + slower "
              "preserving moves; strong form at the root (archive "
              "tier); a weak-form RECORD would need entry=key with "
              "the fork one move deeper")
    else:
        print("  verdict: SINGLE-KEY DECOY -- tempting moves break; "
              "off-paradigm for the pool (interesting, not ours)")
    if n_unknown:
        print(f"  [{dt:.0f}s; {n_unknown} root(s) hit proof budget -- "
              f"raise --budget for harder proofs]")
    else:
        print(f"  [{dt:.0f}s]")

# ------------------------------------------------------------ interaction --

HELP = """commands:
  <any text>     paste anything; every FEN found in it is analysed
  depth N        engine probe depth (default 18; 12 = faster hints)
  horizon N      exact-proof horizon (default 3)
  budget N       node budget per root move (default 300000)
  help           this text
  q / quit       leave
Notes: bare board fields auto-complete to 'w - - 0 1'.
Lines with no FEN and no command are ignored silently (paste-safe)."""

def handle(line: str, eng: Engine, state: dict) -> bool:
    """Returns True if the session should quit."""
    if not line.strip() or line.strip().startswith("#"):
        return False
    low = line.strip().lower()
    if low in ("q", "quit", "exit"):
        return True
    if low in ("h", "help"):
        print(HELP)
        return False
    toks = line.split(None, 1)
    if toks[0].lower() in ("depth", "horizon", "budget") \
            and len(toks) > 1 and toks[1].strip().isdigit():
        key = toks[0].lower()
        state[key] = int(toks[1])
        print(f"{key} -> {state[key]}")
        return False
    fens = extract_fens(line)
    if not fens:
        return False            # silently ignore paste noise
    for fen, auto in fens:
        try:
            analyse(fen, auto, eng, state["depth"], state["horizon"],
                    state["budget"])
        except Exception as exc:
            print(f"  ANALYSIS ERROR on this position ({exc!r}); "
                  f"skipping it, session continues")
    return False

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="interactive FEN evaluator "
                                            "(Einstellung doctrine)")
    ap.add_argument("batch", nargs="?", default=None,
                    help="raw text file; every FEN in it is analysed")
    ap.add_argument("--engine", default=DEFAULT_ENGINE)
    ap.add_argument("--depth", type=int, default=18)
    ap.add_argument("--horizon", type=int, default=3)
    ap.add_argument("--budget", type=int, default=300000)
    args = ap.parse_args(argv)

    if not pathlib.Path(args.engine).exists():
        raise SystemExit(f"engine not found: {args.engine}")

    state = {"depth": args.depth, "horizon": args.horizon,
             "budget": args.budget}
    eng = Engine(args.engine)
    try:
        if args.batch:
            text = pathlib.Path(args.batch).read_text(
                encoding="utf-8-sig", errors="replace")
            for line in text.splitlines():
                try:
                    if handle(line, eng, state):
                        break
                except KeyboardInterrupt:
                    print("  [aborted this line; continuing batch]")
        else:
            print(f"fen_eval v{VERSION} -- paste anything containing "
                  f"FENs, or 'help'. Ctrl+C aborts a position, "
                  f"'q' quits.")
            while True:
                try:
                    line = input("\nfen> ")
                except EOFError:
                    break
                try:
                    if handle(line, eng, state):
                        break
                except KeyboardInterrupt:
                    print("  [aborted; partial results discarded]")
    finally:
        eng.close()
    return 0

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())