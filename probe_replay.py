#!/usr/bin/env python3
"""Probe 2: replay the oracle's first-move engine searches, one change at a time.

    python probe_replay.py RECORD.json TARGET_SAN --engine PATH [--depth 24] [--cap 300]
                           [--hash 256] [--only] [--newgame]

Default: search every legal first move in the oracle's order on ONE shared engine, stopping after
TARGET_SAN (or at the first search that hits the cap).  Each search is sent the way oracle.sf_len sends it
(analyse, Limit(depth, time=cap), root_moves=[move]).
    --only      search only TARGET_SAN (no earlier searches on the engine)
    --hash MB   engine Hash option (the oracle uses 256; the engine default is 16)
    --newgame   send ucinewgame before every search (the oracle never does)
Diagnostic only; it certifies nothing.
"""
import argparse
import json
import sys
import time

import chess
import chess.engine


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("target")
    ap.add_argument("--engine", required=True)
    ap.add_argument("--depth", type=int, default=24)
    ap.add_argument("--cap", type=float, default=300.0)
    ap.add_argument("--hash", type=int, default=256)
    ap.add_argument("--only", action="store_true")
    ap.add_argument("--newgame", action="store_true")
    a = ap.parse_args()

    rec = json.load(open(a.record, encoding="utf-8"))
    b = chess.Board(rec["fen"])
    eng = chess.engine.SimpleEngine.popen_uci(a.engine)
    try:
        eng.configure({"Threads": 1, "Hash": a.hash})
        print(f"{rec['id']}  target {a.target}  depth {a.depth}  cap {a.cap}s  hash {a.hash}  "
              f"only={a.only}  newgame={a.newgame}  engine={eng.id.get('name')}", flush=True)
        moves = [m for m in b.legal_moves]
        if a.only:
            moves = [m for m in moves if b.san(m) == a.target]
        n = 0
        for mv in moves:
            san = b.san(mv)
            t0 = time.time()
            kw = {"game": object()} if a.newgame else {}
            info = eng.analyse(b, chess.engine.Limit(depth=a.depth, time=a.cap), root_moves=[mv], **kw)
            secs = time.time() - t0
            reached = info.get("depth", a.depth)
            n += 1
            flag = " TIMEOUT" if reached < a.depth else ""
            print(f"  {n:2}. {san:8} {secs:6.1f}s  depth {reached}{flag}", flush=True)
            if flag:
                print("  stopped: this search hit the cap", flush=True)
                break
            if san == a.target:
                print("  target finished normally", flush=True)
                break
    finally:
        eng.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())