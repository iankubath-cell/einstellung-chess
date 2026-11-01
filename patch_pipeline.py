#!/usr/bin/env python3
"""Add an engine time cap to pipeline.py and pipeline_config.json (two exact edits plus one config key).

Run once, from the project folder:   python patch_pipeline.py
Backs both files up first.  Each replacement must match exactly once, else nothing is written.
"""
import hashlib
import shutil
import sys
from pathlib import Path

PIPE, CFG = Path("pipeline.py"), Path("pipeline_config.json")

PIPE_EDITS = [
    ("    oc = pl.oracle()\n"
     "    try:\n"
     "        return oc.judge(cand, budget=budget, engine=pl.engine() if use_engine else None,\n"
     "                        depth=depth, engine_info=pl._engine_info, fast=fast)\n",
     "    oc = pl.oracle()\n"
     "    tmo = pl.cfg[\"certify\"].get(\"engine_timeout\") if use_engine else None\n"
     "    try:\n"
     "        return oc.judge(cand, budget=budget, engine=pl.engine() if use_engine else None,\n"
     "                        depth=depth, engine_info=pl._engine_info, fast=fast, engine_timeout=tmo)\n"),
    ("        return oc.judge(cand, budget=budget, engine=pl.engine(),\n"
     "                        depth=depth, engine_info=pl._engine_info, fast=fast)\n",
     "        return oc.judge(cand, budget=budget, engine=pl.engine(),\n"
     "                        depth=depth, engine_info=pl._engine_info, fast=fast, engine_timeout=tmo)\n"),
]
CFG_EDITS = [
    ('"certify": {"depth": 24, "budget": 15000000, "engine": true},',
     '"certify": {"depth": 24, "budget": 15000000, "engine": true, "engine_timeout": 300},'),
]


def load(p):
    raw = p.read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), (b"\r\n" in raw)


def apply(s, edits, name):
    for old, new in edits:
        n = s.count(old)
        if n != 1:
            sys.exit(f"STOP: {name}: expected the text exactly once, found {n} times. Nothing was changed.\n"
                     f"Looking for:\n{old}")
        s = s.replace(old, new)
    return s


def main():
    ps, pcr = load(PIPE)
    cs, ccr = load(CFG)
    ps2, cs2 = apply(ps, PIPE_EDITS, "pipeline.py"), apply(cs, CFG_EDITS, "pipeline_config.json")
    compile(ps2, "pipeline.py", "exec")                       # must still be valid Python
    import json
    json.loads(cs2)                                           # must still be valid JSON
    for p, bak in ((PIPE, "pipeline_before_timeout.py"), (CFG, "pipeline_config_before_timeout.json")):
        if Path(bak).exists():
            sys.exit(f"STOP: {bak} already exists; move it away first. Nothing was changed.")
    shutil.copy2(PIPE, "pipeline_before_timeout.py")
    shutil.copy2(CFG, "pipeline_config_before_timeout.json")
    for p, s, cr in ((PIPE, ps2, pcr), (CFG, cs2, ccr)):
        out = s.replace("\n", "\r\n") if cr else s
        p.write_bytes(out.encode("utf-8"))
        print(f"patched {p}  sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")
    print("backups: pipeline_before_timeout.py, pipeline_config_before_timeout.json")


main()