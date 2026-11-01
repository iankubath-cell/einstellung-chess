#!/usr/bin/env python3
"""Probe: run ONE root-restricted engine search on a fresh engine and print every depth as it completes.

    python probe_search.py RECORD.json MOVE_SAN --engine PATH --depth 24 --timeout 120

Purpose: tell apart "this search is stuck whatever happened before" from "it stalls only after earlier
searches on the same engine".  Diagnostic only; it certifies nothing.
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
    ap.add_argument("move")
    ap.add_argument("--engine", required=True)
    ap.add_argument("--depth", type=int, default=24)
    ap.add_argument("--timeout", type=float, default=120.0)
    a = ap.parse_args()

    rec = json.load(open(a.record, encoding="utf-8"))
    b = chess.Board(rec["fen"])
    mv = b.parse_san(a.move)
    eng = chess.engine.SimpleEngine.popen_uci(a.engine)
    try:
        print("engine:", eng.id.get("name"), "| Threads", eng.options["Threads"].default if "Threads" in eng.options else "?",
              "| Hash", eng.options["Hash"].default if "Hash" in eng.options else "?", flush=True)
        print(f"{rec['id']}  root move {a.move}  target depth {a.depth}  cap {a.timeout}s  (fresh engine)", flush=True)
        t0 = time.time()
        last = 0
        with eng.analysis(b, chess.engine.Limit(depth=a.depth), root_moves=[mv]) as an:
            for info in an:
                d = info.get("depth")
                if d and d != last and "score" in info:
                    last = d
                    print(f"  depth {d:2}  {time.time() - t0:7.1f}s  score {info['score'].white()}  nodes {info.get('nodes')}",
                          flush=True)
                if time.time() - t0 > a.timeout:
                    print(f"  STOPPED at {a.timeout}s, last depth {last}", flush=True)
                    an.stop()
                    break
        print(f"finished in {time.time() - t0:.1f}s, last depth {last}", flush=True)
    finally:
        eng.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())