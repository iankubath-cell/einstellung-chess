#!/usr/bin/env python3
"""pipeline.py -- unattended Einstellung pipeline (v0.3)

Runs the whole loop -- compose -> lint -> filter -> certify -> manifest --
without a chat session attached, so multi-hour runs survive rate limits,
sleep, reboots and crashes.

Design rules (each one is a scar from this project's history):
  * every stage writes ONE SMALL FILE PER CANDIDATE, so a killed run resumes
    by skipping whatever already exists.  Nothing is ever redone wholesale.
  * all output STREAMS to per-stage logs and the console.  Never buffered to
    process end.
  * a LOCK FILE plus PID identifies the one live run.  Kill by PID, never by
    pattern-match.  A second pipeline instance refuses to start while the
    lock is held by a live process.
  * every input file is HASHED into provenance.json BEFORE work starts, so a
    result always traces to the exact code that produced it.
  * the oracle is IMPORTED, not shelled out to, so one engine launch serves
    hundreds of candidates.  If the engine dies mid-run it is reopened once
    per candidate before the run gives up on it.
  * lint is STRICT: it regenerates SAN from the board and compares.  This is
    the check that catches Na6+ where the position demands Nxa6+.
  * candidate ids are sanitised before they become filenames.

Changelog v0.2 -> v0.3 (composer.py arrived with a real CLI):
  * compose is now TWO steps, matching composer.py's actual interface:
    search_command writes a raw file, finalize_command turns it into
    per-survivor E-*.json files.  The old single 'command' key still works
    if that is all the config has.
  * NEW config key paths.survivors_dir: when set, lint/filter/certify read
    candidates from that folder instead of this run's compose stage.  This
    is how you verify Claude's 349 survivors without generating anything.
  * index.json files in survivor folders are skipped instead of being fed
    to the tolerant reader (finalize writes one; it is a summary, not a
    candidate).
  * preflight hashes the survivors folder too when it is configured, so
    the manifest records exactly which candidate set a run consumed.

Changelog v0.1 -> v0.2 (bug fixes, same on-disk layout):
  * manifest lint tally used the literal string "clean" as a key; now
    tallies True/False correctly.
  * resumed runs reload state.json, so a manifest after --run X shows all
    steps of that run.
  * lint counts derive from the index for fresh and resumed candidates alike.
  * certify retries once through an engine reopen before recording failure.
  * duplicate candidate ids across survivor files are deduplicated loudly.
  * missing executables give a clear message, not a traceback.
  * Ctrl-C records partial state and exits 130.

Commands
  init        write a pipeline_config.json template and exit
  preflight   hash inputs, check imports and engine, print provenance
  compose     run the decoration search (search + finalize, from config)
  lint        strict SAN check on survivors
  filter      oracle fast mode, python-only
  certify     oracle two-engine at full depth (slow, resumable)
  manifest    aggregate everything into manifest.json
  commit      git add/commit the run (opt-in via config)
  all         preflight -> compose -> lint -> filter -> certify -> manifest
  status      show progress of recent runs

Typical use
  python pipeline.py init
  python pipeline.py preflight          # sanity-check before a long run
  python pipeline.py all                # walk away; check back later
  python pipeline.py status
  python pipeline.py certify             # re-enter just the slow stage
  python pipeline.py manifest --run 20261030-191200

Everything lands under runs/<YYYYMMDD-HHMMSS>/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
VERSION = "0.3"
CONFIG_NAME = "pipeline_config.json"
RUNS_ROOT = "runs"
LOCK_NAME = "pipeline.lock"
SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
SKIP_FILES = {"index.json", "manifest.json", "provenance.json", "state.json"}

CONFIG_TEMPLATE: Dict[str, Any] = {
    "_comment": "Paths are relative to this file's folder.",
    "paths": {
        "oracle": "oracle.py",
        "skeleton": "composer_skeleton.py",
        "canonical": "positions/canonical.json",
        "rejects": "fixtures/rejects.json",
        "stockfish": "C:/Users/44777/Downloads/stockfish-windows-x86-64-universal/stockfish/stockfish-windows-x86-64-universal.exe",
        "evidence_dir": "docs/outputs",
        "survivors_dir": "",
    },
    "compose": {
        "enabled": False,
        "search_command": [
            "python", "composer.py", "search",
            "--mode", "unguided", "--seed", "1", "--evals", "400",
            "--out", "{out}/raw_seed1.json",
        ],
        "finalize_command": [
            "python", "composer.py", "finalize",
            "--raw", "{out}/raw_seed1.json",
            "--out", "{out}",
        ],
        "_note": ("{out} is replaced with the compose stage folder. "
                  "Both commands must exist and be lists. To verify an "
                  "existing survivor set instead, leave enabled=false and "
                  "set paths.survivors_dir."),
    },
    "filter": {"budget": 5000000},
    "certify": {"depth": 24, "budget": 15000000, "engine": True},
    "commit": {"enabled": False, "message_prefix": "Pipeline run"},
}


# --------------------------------------------------------------------- basics

def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(HERE))
    except ValueError:
        return str(p)


def safe_id(raw: str) -> str:
    s = SAFE_ID.sub("_", str(raw)).strip("._") or "cand"
    return s[:120]


def child_env() -> Dict[str, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def pid_alive(pid: int) -> bool:
    """Best-effort liveness check with no third-party deps."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=15,
            ).stdout
            return str(pid) in out
        os.kill(pid, 0)          # POSIX: raises if dead
        return True
    except Exception:
        return False


class Lock:
    """Single-instance guard. Writes runs/pipeline.lock; refuses if a live PID holds it."""

    def __init__(self, root: Path):
        self.path = root / LOCK_NAME
        self.held = False

    def acquire(self) -> None:
        if self.path.exists():
            try:
                old = json.loads(self.path.read_text(encoding="utf-8"))
                old_pid = int(old.get("pid", -1))
            except Exception:
                old_pid = -1
            if old_pid > 0 and pid_alive(old_pid):
                raise SystemExit(
                    f"another pipeline instance appears to be running (PID {old_pid}, "
                    f"started {old.get('started', '?')}). If you are SURE it is dead, "
                    f"delete {self.path} and try again.")
            print(f"removing stale lock (PID {old_pid} is not alive)")
        self.path.write_text(json.dumps(
            {"pid": os.getpid(),
             "started": datetime.now().isoformat(timespec="seconds"),
             "host": platform.node()}), encoding="utf-8")
        self.held = True

    def release(self) -> None:
        if self.held and self.path.exists():
            try:
                mine = json.loads(self.path.read_text(encoding="utf-8"))
                if int(mine.get("pid", -1)) == os.getpid():
                    self.path.unlink()
            except Exception:
                pass
        self.held = False


def run_stream(cmd: List[str], log_path: Path, dry: bool = False) -> Tuple[int, float]:
    """Run a command, echoing every line to console AND log. Returns (rc, seconds)."""
    printable = " ".join(shlex.quote(str(c)) for c in cmd)
    print(f"[cmd] {printable}")
    if dry:
        return 0, 0.0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.Popen(
            [str(c) for c in cmd], cwd=str(HERE), env=child_env(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
    except FileNotFoundError:
        msg = f"command not found: {cmd[0]}"
        with open(log_path, "a", encoding="utf-8", errors="replace") as lg:
            lg.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} {printable}\n{msg}\n")
        print(f"  ERROR {msg}")
        return 127, 0.0
    t0 = time.time()
    with open(log_path, "a", encoding="utf-8", errors="replace") as lg:
        lg.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} {printable}\n")
        lg.flush()
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lg.write(line)
            lg.flush()
        rc = proc.wait()
    return rc, time.time() - t0


# ---------------------------------------------------------------- config/run

def validate_config(cfg: Dict[str, Any]) -> None:
    problems: List[str] = []
    for section in ("paths", "compose", "filter", "certify", "commit"):
        if section not in cfg:
            problems.append(f"missing section '{section}'")
    if problems:
        raise SystemExit("invalid pipeline_config.json:\n  " + "\n  ".join(problems))

    comp = cfg["compose"]
    if comp.get("enabled", False):
        if "search_command" in comp or "finalize_command" in comp:
            for key in ("search_command", "finalize_command"):
                c = comp.get(key)
                if not isinstance(c, list) or not c:
                    raise SystemExit(f"invalid pipeline_config.json: compose.{key} "
                                     "must be a non-empty list")
                if "{out}" not in [str(x) for x in c]:
                    print(f"  warning: compose.{key} has no {{out}} placeholder")
        elif "command" in comp:
            if not isinstance(comp.get("command"), list) or not comp["command"]:
                raise SystemExit("invalid pipeline_config.json: compose.command "
                                 "must be a non-empty list")
        else:
            raise SystemExit("invalid pipeline_config.json: compose is enabled but has "
                             "no search_command/finalize_command/command")

    sd = cfg["paths"].get("survivors_dir") or ""
    if sd and not (HERE / sd).exists():
        print(f"  warning: paths.survivors_dir does not exist yet: {sd}")


class Pipeline:
    def __init__(self, cfg: Dict[str, Any], run_dir: Path, dry: bool = False):
        self.cfg = cfg
        self.dry = dry
        self.paths = cfg["paths"]
        self.run_dir = run_dir
        self.steps: Dict[str, Dict[str, Any]] = {}
        self._oracle = None
        self._engine = None
        self._engine_info: Optional[Dict[str, str]] = None
        self._load_state()

    # -- path helpers
    def p(self, key: str) -> Path:
        return HERE / self.paths[key]

    def stage(self, name: str) -> Path:
        d = self.run_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def log(self, name: str) -> Path:
        return self.run_dir / "logs" / f"{name}.log"

    def survivors_source(self) -> Path:
        """Where candidates come from: config survivors_dir, else this run's compose."""
        sd = self.paths.get("survivors_dir") or ""
        if sd:
            return HERE / sd
        return self.stage("compose")

    # -- state (survives interruption; reloaded on resume)
    def _load_state(self) -> None:
        sp = self.run_dir / "state.json"
        if sp.exists():
            try:
                doc = json.loads(sp.read_text(encoding="utf-8"))
                self.steps = doc.get("steps", {})
            except Exception as exc:
                print(f"warning: could not read {rel(sp)} ({exc!r}); starting fresh step log")

    def record(self, step: str, rc: int, seconds: float, **extra) -> None:
        prev = self.steps.get(step, {})
        merged = {**prev, "exit": rc, "seconds": round(seconds, 1), **extra}
        self.steps[step] = merged
        self.save_state()

    def save_state(self) -> None:
        if self.dry:
            return
        doc = {
            "pipeline_version": VERSION,
            "run_id": self.run_dir.name,
            "updated": datetime.now().isoformat(timespec="seconds"),
            "steps": self.steps,
        }
        tmp = self.run_dir / "state.json.tmp"
        tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        tmp.replace(self.run_dir / "state.json")   # atomic-ish: no torn file

    # -- oracle access
    def oracle(self):
        if self._oracle is None:
            op = self.p("oracle")
            if not op.exists():
                raise SystemExit(f"oracle not found: {op}")
            if op.stem in sys.modules:
                del sys.modules[op.stem]     # always reload the pinned file
            sys.path.insert(0, str(op.parent))
            import importlib
            self._oracle = importlib.import_module(op.stem)
        return self._oracle

    def engine(self):
        if self._engine is None and self.cfg["certify"].get("engine", True):
            sf = self.paths.get("stockfish") or ""
            if not sf:
                raise SystemExit("certify.engine is true but paths.stockfish is empty. "
                                 "Set it in pipeline_config.json.")
            if not Path(sf).exists():
                raise SystemExit(f"stockfish path in config does not exist: {sf}")
            self._engine, self._engine_info = self.oracle().open_engine(sf, threads=1, hash_mb=256)
        return self._engine

    def reopen_engine(self) -> bool:
        """Quit whatever is there and start a fresh engine. False if it cannot be done."""
        self.close_engine()
        try:
            self.engine()
            print("  [engine reopened]")
            return True
        except SystemExit as exc:
            print(f"  [engine reopen failed: {exc}]")
            return False

    def close_engine(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None


# ------------------------------------------------------------------ preflight

def preflight(pl: Pipeline) -> int:
    print(f"pipeline v{VERSION}  run {pl.run_dir.name}")
    print(f"python {platform.python_version()} on {platform.system()} {platform.release()}")
    prov: Dict[str, Any] = {
        "pipeline_version": VERSION,
        "run_id": pl.run_dir.name,
        "started": datetime.now().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "inputs": {},
        "imports": {},
    }

    ok = True
    for key in ("oracle", "skeleton", "canonical", "rejects"):
        path = pl.p(key)
        if path.exists():
            prov["inputs"][rel(path)] = sha256_file(path)
            print(f"  ok   {rel(path)}  {prov['inputs'][rel(path)][:16]}...")
        else:
            print(f"  MISS {rel(path)}")
            ok = False

    for name in ("composer.py", "pipeline.py"):
        cand = HERE / name
        if cand.exists():
            prov["inputs"][name] = sha256_file(cand)
            print(f"  ok   {name}  {prov['inputs'][name][:16]}...")
        elif name == "composer.py" and pl.cfg["compose"].get("enabled", False):
            print(f"  MISS {name} (compose is enabled in config)")
            ok = False

    sd = pl.paths.get("survivors_dir") or ""
    if sd:
        src = HERE / sd
        if src.is_dir():
            files = [f for f in sorted(src.glob("*.json"))
                     if f.name not in SKIP_FILES and not f.name.startswith("index")]
            prov["survivors_dir"] = {"path": sd, "files": len(files),
                                     "sha256_of_sorted_concat": _dir_digest(files)}
            print(f"  ok   survivors_dir {sd}: {len(files)} candidate file(s)")
        else:
            print(f"  MISS survivors_dir {sd} (configured but absent)")
            ok = False

    try:
        import chess
        prov["imports"]["python_chess"] = chess.__version__
        print(f"  ok   python-chess {chess.__version__}")
    except Exception as exc:
        prov["imports"]["python_chess"] = f"MISSING: {exc!r}"
        print(f"  MISS python-chess ({exc!r})")
        ok = False

    sf = pl.paths.get("stockfish") or ""
    if sf and Path(sf).exists():
        prov["stockfish_path"] = sf
        try:
            eng, info = pl.oracle().open_engine(sf, threads=1, hash_mb=256)
            prov["engine"] = info
            eng.quit()
            print(f"  ok   engine {info.get('engine_id')} "
                  f"(threads {info.get('threads')}, hash {info.get('hash')})")
        except Exception as exc:
            prov["engine"] = f"FAILED TO OPEN: {exc!r}"
            print(f"  MISS engine open failed: {exc!r}")
            ok = False
    else:
        print("  note no stockfish configured -- certify will not be possible")
        prov["engine"] = "not configured"

    if not pl.dry:
        (pl.run_dir / "provenance.json").write_text(
            json.dumps(prov, indent=2), encoding="utf-8")
    print(f"\npreflight {'OK' if ok else 'INCOMPLETE'} -- provenance written")
    pl.record("preflight", 0 if ok else 1, 0.0, ok=ok)
    return 0 if ok else 1


def _dir_digest(files: List[Path]) -> str:
    """Order-stable digest of a folder's contents, so the manifest pins the input set."""
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


# -------------------------------------------------------------------- compose

def _fill(cmd: List[str], out: Path) -> List[str]:
    return [str(c).replace("{out}", str(out)) for c in cmd]


def compose(pl: Pipeline) -> int:
    spec = pl.cfg["compose"]
    if not spec.get("enabled", False):
        src = pl.survivors_source()
        print(f"compose disabled in config; candidates will be read from {rel(src)}")
        pl.record("compose", 0, 0.0, skipped=True)
        return 0
    out = pl.stage("compose")

    t0 = time.time()
    if "search_command" in spec or "finalize_command" in spec:
        rc, secs = run_stream(_fill(spec["search_command"], out), pl.log("compose"), pl.dry)
        pl.record("compose-search", rc, secs)
        if rc != 0:
            print(f"search failed (exit {rc}); not running finalize")
            pl.record("compose", rc, time.time() - t0)
            return rc
        rc, secs = run_stream(_fill(spec["finalize_command"], out), pl.log("compose"), pl.dry)
        pl.record("compose-finalize", rc, secs)
        if rc != 0:
            pl.record("compose", rc, time.time() - t0)
            return rc
    else:
        rc, secs = run_stream(_fill(spec["command"], out), pl.log("compose"), pl.dry)
        pl.record("compose", rc, secs)
        if rc != 0:
            return rc

    n = len([f for f in out.iterdir() if f.is_file() and f.suffix == ".json"])
    pl.record("compose", 0, time.time() - t0, files=n)
    print(f"compose done, {n} json file(s) in {rel(out)}")
    if n == 0 and not pl.dry:
        print("  warning: compose produced no files -- check the commands' "
              "output flags in pipeline_config.json")
    return 0


# ----------------------------------------------------------------------- lint

def _sans_of(value: Any) -> List[str]:
    if isinstance(value, dict):
        for k in ("san", "SAN", "moves", "line"):
            if isinstance(value.get(k), list):
                return [str(x) for x in value[k]]
            if isinstance(value.get(k), str):
                return value[k].split()
        return []
    if isinstance(value, str):
        return value.split()
    return [str(x) for x in (value or [])]


def _first_key(d: Dict[str, Any], names) -> Any:
    for n in names:
        if n in d and d[n] not in (None, ""):
            return d[n]
    return None


def load_survivors(path: Path) -> List[Dict[str, Any]]:
    """Tolerant reader. Raises ValueError with the keys it DID find, so adapting is quick."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: invalid JSON ({exc})") from None
    if isinstance(doc, dict):
        items = None
        for key in ("survivors", "candidates", "positions", "results", "items"):
            if isinstance(doc.get(key), list):
                items = doc[key]
                break
        if items is None:
            items = [doc]
    elif isinstance(doc, list):
        items = doc
    else:
        raise ValueError(f"{path.name}: unexpected JSON shape {type(doc).__name__}")

    out = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise ValueError(f"{path.name}: item {i} is {type(it).__name__}, not an object")
        fen = _first_key(it, ("fen", "FEN", "position"))
        first = _first_key(it, ("first_move", "first", "shared_first_move", "move"))
        declared = _first_key(it, ("declared", "lengths", "declared_lengths"))
        lines = _first_key(it, ("lines", "san_lines", "line")) or {}
        cid = _first_key(it, ("id", "candidate_id", "name", "key")) or f"cand{i:04d}"
        if not (fen and first and declared):
            raise ValueError(
                f"{path.name}: cannot read survivor {i} (id={cid}). "
                f"keys present: {sorted(it)}. "
                f"need fen/first_move/declared -- add aliases in load_survivors().")
        try:
            decl = {str(k): int(v) for k, v in dict(declared).items()}
        except (TypeError, ValueError):
            raise ValueError(f"{path.name}: survivor {i} (id={cid}) has "
                             f"unreadable 'declared': {declared!r}") from None
        out.append({
            "id": str(cid), "safe_id": safe_id(cid), "fen": str(fen),
            "first_move": str(first), "declared": decl,
            "lines": {str(k): _sans_of(v) for k, v in dict(lines).items()},
            "raw": it,
        })
    return out


def gather_candidates(pl: Pipeline) -> List[Dict[str, Any]]:
    """All survivors from the source folder, deduplicated by id, problems reported once."""
    src = pl.survivors_source()
    if not src.is_dir():
        print(f"no candidate source folder: {rel(src)}")
        return []
    files = [f for f in sorted(list(src.glob("*.json")) + list(src.glob("*.jsonl")))
             if f.name not in SKIP_FILES and not f.name.startswith("index")]
    cands: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}
    for f in files:
        try:
            batch = load_survivors(f)
        except ValueError as exc:
            print(f"  SKIP {exc}")
            continue
        for c in batch:
            if c["id"] in seen:
                if seen[c["id"]] != f.name:
                    print(f"  DUP  {c['id']} appears in {seen[c['id']]} and {f.name}; keeping first")
                continue
            seen[c["id"]] = f.name
            cands.append(c)
    return cands


def lint_line(fen: str, sans: List[str]) -> List[Dict[str, Any]]:
    """Regenerate SAN from the board and compare. Catches Na6+ that should be Nxa6+."""
    import chess
    problems: List[Dict[str, Any]] = []
    try:
        b = chess.Board(fen)
    except ValueError as exc:
        return [{"ply": 0, "token": "", "problem": f"invalid FEN: {exc}"}]
    for ply, tok in enumerate(sans, 1):
        try:
            mv = b.parse_san(tok)
        except ValueError as exc:
            problems.append({"ply": ply, "token": tok, "problem": f"unparseable: {exc}"})
            break
        canonical = b.san(mv)
        if canonical != tok:
            problems.append({
                "ply": ply, "token": tok, "problem": "non-standard SAN",
                "expected": canonical,
                "kind": "capture_mark" if canonical.replace("x", "") == tok.replace("x", "")
                        else "other",
            })
        b.push(mv)
    return problems


def lint(pl: Pipeline) -> int:
    stage = pl.stage("lint")
    cands = gather_candidates(pl)
    if not cands:
        print("no survivors found -- nothing to lint")
        pl.record("lint", 0, 0.0, examined=0, flagged=0)
        return 0
    print(f"linting {len(cands)} candidate(s) from {rel(pl.survivors_source())}")

    index_path = stage / "index.jsonl"
    done: Dict[str, bool] = {}
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["id"]] = rec["clean"]

    t0 = time.time()
    newly = 0
    with open(index_path, "a", encoding="utf-8") as idx:
        for i, cand in enumerate(cands, 1):
            sid = cand["safe_id"]
            if cand["id"] in done:
                continue
            probs = lint_line(cand["fen"], [cand["first_move"]])
            for key, sans in cand["lines"].items():
                for pr in lint_line(cand["fen"], sans):
                    probs.append({"line": key, **pr})
            rec = {"id": cand["id"], "safe_id": sid, "clean": not probs, "problems": probs}
            (stage / f"{sid}.json").write_text(
                json.dumps(rec, indent=2), encoding="utf-8")
            idx.write(json.dumps({"id": cand["id"], "clean": rec["clean"]}) + "\n")
            idx.flush()
            done[cand["id"]] = rec["clean"]
            newly += 1
            if probs:
                for pr in probs[:3]:
                    print(f"  FLAG {cand['id']}: ply {pr.get('ply')} "
                          f"'{pr.get('token')}' -> {pr.get('problem')}"
                          + (f" (should be {pr['expected']})" if pr.get("expected") else ""))
            if i % 50 == 0:
                print(f"  ... {i}/{len(cands)} linted")

    total = len(done)
    flagged = sum(1 for v in done.values() if not v)
    secs = time.time() - t0
    print(f"\nlint: {total} candidate(s) examined ({newly} fresh this pass), "
          f"{flagged} flagged, {total - flagged} clean")
    print(f"index: {rel(index_path)}")
    pl.record("lint", 0, secs, examined=total, flagged=flagged)
    return 0


# --------------------------------------------------------------- filter/cert

def _clean_ids(pl: Pipeline) -> set:
    """Ids that passed lint (from the lint index, tolerating a skipped lint stage)."""
    idx = pl.run_dir / "lint" / "index.jsonl"
    if not idx.exists():
        return set()      # lint never ran: caller decides what that means
    out = set()
    for line in idx.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            if rec["clean"]:
                out.add(rec["id"])
    return out


def _load_stage_index(pl: Pipeline, stage_name: str) -> Dict[str, str]:
    idx = pl.run_dir / stage_name / "index.jsonl"
    if not idx.exists():
        return {}
    out: Dict[str, str] = {}
    for line in idx.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["id"]] = rec.get("status", "?")
    return out


def _verdict_text(v) -> str:
    lines = [f"status={v.status}", f"codes={v.codes}", f"nodes={v.nodes}",
             f"tier={v.evidence_tier}", f"budget={v.budget}", ""]
    for ch in v.checks:
        lines.append(f"{'PASS' if ch.ok else 'FAIL'} {ch.name}  {ch.detail}")
    for cv in v.caveats:
        lines.append(f"CAVEAT {cv}")
    lines += ["", f"meta={v.meta}"]
    return "\n".join(lines)


def _judge_with_engine_retry(pl: Pipeline, cand, fast: bool, use_engine: bool,
                             depth: int, budget: int):
    """judge() with one engine reopen+retry if the engine died mid-run."""
    oc = pl.oracle()
    try:
        return oc.judge(cand, budget=budget, engine=pl.engine() if use_engine else None,
                        depth=depth, engine_info=pl._engine_info, fast=fast)
    except SystemExit:
        raise
    except Exception as first:
        if not use_engine:
            raise
        print(f"  [judge failed on {cand.id}: {first!r}; reopening engine and retrying once]")
        if not pl.reopen_engine():
            raise
        return oc.judge(cand, budget=budget, engine=pl.engine(),
                        depth=depth, engine_info=pl._engine_info, fast=fast)


def _run_oracle_stage(pl: Pipeline, stage_name: str, fast: bool, use_engine: bool) -> int:
    stage = pl.stage(stage_name)
    cands = gather_candidates(pl)
    if not cands:
        print(f"{stage_name}: no candidates found at all")
        return 1

    # eligibility
    clean = _clean_ids(pl)
    if pl.run_dir.joinpath("lint", "index.jsonl").exists():
        if not clean:
            print(f"{stage_name}: lint ran but flagged/pass-recorded nothing -- "
                  "check the lint stage output")
        cands = [c for c in cands if c["id"] in clean]
    else:
        print("  note: lint index absent -- running on ALL survivors "
              "(run 'lint' first for the strict SAN gate)")
    if stage_name == "certify":
        passed = {i for i, s in _load_stage_index(pl, "filter").items() if s == "PASS"}
        if pl.run_dir.joinpath("filter", "index.jsonl").exists():
            if not passed:
                print("certify: filter ran but recorded no PASS candidates -- nothing to do")
                pl.record("certify", 0, 0.0, counts={}, note="no filter passes")
                return 0
            cands = [c for c in cands if c["id"] in passed]
        else:
            print("  warning: filter index absent -- certifying ALL lint-clean candidates")

    if not cands:
        print(f"{stage_name}: no eligible candidates")
        return 0

    status_so_far = _load_stage_index(pl, stage_name)
    todo = [c for c in cands if c["id"] not in status_so_far]
    print(f"{stage_name}: {len(cands)} eligible, {len(cands) - len(todo)} already done, "
          f"{len(todo)} to run")

    eng = None
    if use_engine:
        try:
            eng = pl.engine()
        except SystemExit as exc:
            print(f"cannot start certify: {exc}")
            return 2
    depth = pl.cfg["certify"]["depth"] if use_engine else 0
    budget = pl.cfg["certify"]["budget"] if use_engine else pl.cfg["filter"]["budget"]

    counts: Dict[str, int] = {}
    for v in status_so_far.values():
        counts[v] = counts.get(v, 0) + 1
    t0 = time.time()
    errors = 0
    with open(stage / "index.jsonl", "a", encoding="utf-8") as idx:
        for i, cand in enumerate(todo, 1):
            sid = cand["safe_id"]
            oc = pl.oracle()
            oc_cand = oc.Candidate(cand["id"], cand["fen"], cand["first_move"],
                                   cand["declared"], cand["lines"])
            status = "ERROR"
            try:
                v = _judge_with_engine_retry(pl, oc_cand, fast, use_engine, depth, budget)
                text = _verdict_text(v)
                status = v.status
            except Exception as exc:
                text = f"status=ERROR\nexception={exc!r}"
                errors += 1
            (stage / f"{sid}.json").write_text(
                json.dumps({"id": cand["id"], "status": status}), encoding="utf-8")
            (stage / f"{sid}.txt").write_text(text, encoding="utf-8")
            idx.write(json.dumps({"id": cand["id"], "status": status}) + "\n")
            idx.flush()
            counts[status] = counts.get(status, 0) + 1
            print(f"  [{i}/{len(todo)}] {cand['id']:24} {status}")
            if errors and errors >= 5 and errors == i:
                print("  too many consecutive failures at the start -- aborting stage")
                pl.record(stage_name, 2, time.time() - t0, counts=counts, errors=errors)
                return 2

    secs = time.time() - t0
    print(f"\n{stage_name}: {counts} in {secs:.1f}s"
          + (f" ({errors} error(s))" if errors else ""))
    pl.record(stage_name, 0, secs, counts=counts, errors=errors)
    return 0


def filter_stage(pl: Pipeline) -> int:
    return _run_oracle_stage(pl, "filter", fast=True, use_engine=False)


def certify(pl: Pipeline) -> int:
    return _run_oracle_stage(pl, "certify", fast=False, use_engine=True)


# ------------------------------------------------------------------- manifest

def manifest(pl: Pipeline) -> int:
    counts: Dict[str, Dict[str, int]] = {}
    # lint tallies its boolean
    lint_idx = pl.run_dir / "lint" / "index.jsonl"
    tally: Dict[str, int] = {}
    if lint_idx.exists():
        for line in lint_idx.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                key = "clean" if rec.get("clean") else "flagged"
                tally[key] = tally.get(key, 0) + 1
    counts["lint"] = tally
    # filter/certify tally statuses
    for stage_name in ("filter", "certify"):
        tally = {}
        for _id, st in _load_stage_index(pl, stage_name).items():
            tally[st] = tally.get(st, 0) + 1
        counts[stage_name] = tally

    prov_path = pl.run_dir / "provenance.json"
    doc = {
        "pipeline_version": VERSION,
        "run_id": pl.run_dir.name,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "provenance": (json.loads(prov_path.read_text(encoding="utf-8"))
                       if prov_path.exists() else {}),
        "steps": pl.steps,
        "counts": counts,
        "note": ("Nothing here is a finding until it shows PASS at two-engine "
                 "tier in the certify stage. Everything else is a candidate."),
    }
    out = pl.run_dir / "manifest.json"
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(counts, indent=2))
    print(f"\nwrote {rel(out)}")
    return 0


# --------------------------------------------------------------------- commit

def commit(pl: Pipeline) -> int:
    if not pl.cfg["commit"].get("enabled", False):
        print("commit disabled in config; nothing done")
        return 0
    man = pl.run_dir / "manifest.json"
    if not man.exists():
        print("no manifest.json yet; run 'manifest' first")
        return 1
    doc = json.loads(man.read_text(encoding="utf-8"))
    msg = (f"{pl.cfg['commit'].get('message_prefix', 'Pipeline run')} {pl.run_dir.name}\n\n"
           f"counts: {json.dumps(doc.get('counts', {}))}\n"
           f"manifest sha256: {sha256_file(man)}")
    for cmd in (["git", "add", "-A", str(pl.run_dir)],
                ["git", "commit", "-m", msg]):
        rc, _ = run_stream(cmd, pl.log("commit"), pl.dry)
        if rc != 0:
            print(f"git step failed (exit {rc}); stopping")
            return rc
    print("committed. push when you are ready:")
    print("  git push")
    return 0


# --------------------------------------------------------------------- status

def status() -> int:
    root = HERE / RUNS_ROOT
    if not root.exists():
        print("no runs yet")
        return 0
    runs = sorted([d for d in root.iterdir() if d.is_dir()], reverse=True)
    for rd in runs[:5]:
        print(f"\nrun {rd.name}")
        state = rd / "state.json"
        if state.exists():
            try:
                doc = json.loads(state.read_text(encoding="utf-8"))
                for name, info in doc.get("steps", {}).items():
                    print(f"  {name:9} exit={info.get('exit')} "
                          f"{info.get('seconds')}s {info.get('counts', '') or ''}")
            except Exception:
                print("  (unreadable state.json)")
        for stage in ("compose", "lint", "filter", "certify"):
            d = rd / stage
            if d.exists():
                n = len([f for f in d.iterdir() if f.is_file()])
                print(f"  {stage:9} {n} file(s)")
    lock = root / LOCK_NAME
    if lock.exists():
        try:
            info = json.loads(lock.read_text(encoding="utf-8"))
            pid = int(info.get("pid", -1))
        except Exception:
            pid = -1
        if pid > 0 and pid_alive(pid):
            print(f"\nLIVE RUN: PID {pid} (started {info.get('started', '?')})")
        else:
            print("\nstale lock present (no live process) -- safe to delete "
                  f"{rel(lock)}")
    return 0


# ----------------------------------------------------------------------- main

def load_config() -> Dict[str, Any]:
    cfg_path = HERE / CONFIG_NAME
    if not cfg_path.exists():
        raise SystemExit(f"no {CONFIG_NAME}. Run: python pipeline.py init")
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {CONFIG_NAME}: {exc}")
    validate_config(cfg)
    return cfg


def cmd_init(_a) -> int:
    cfg_path = HERE / CONFIG_NAME
    if cfg_path.exists():
        print(f"{CONFIG_NAME} already exists; not overwriting")
        return 0
    cfg_path.write_text(json.dumps(CONFIG_TEMPLATE, indent=2), encoding="utf-8")
    print(f"wrote {CONFIG_NAME}")
    print("If you only want to VERIFY existing survivors: set paths.survivors_dir "
          "and leave compose.enabled=false.")
    print("To GENERATE: set compose.enabled=true and check the search/finalize commands.")
    return 0


STEPS = {
    "preflight": preflight, "compose": compose, "lint": lint,
    "filter": filter_stage, "certify": certify,
    "manifest": manifest, "commit": commit,
}
ORDER = ["preflight", "compose", "lint", "filter", "certify", "manifest"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", default=None, help="existing run id to resume")
    ap.add_argument("--dry-run", action="store_true", help="print commands, run nothing")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "preflight", "compose", "lint", "filter", "certify",
                 "manifest", "commit", "all", "status"):
        sub.add_parser(name)
    a = ap.parse_args(argv)

    if a.cmd == "init":
        return cmd_init(a)
    if a.cmd == "status":
        return status()

    cfg = load_config()
    root = HERE / RUNS_ROOT
    root.mkdir(exist_ok=True)
    if a.run:
        run_dir = root / a.run
        if not run_dir.exists():
            raise SystemExit(f"no such run: {a.run}")
    else:
        run_dir = root / stamp()
        if run_dir.exists():                     # clock tick collision
            run_dir = root / f"{stamp()}-{os.getpid()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    lock = Lock(root)
    if not a.dry_run:
        lock.acquire()

    pl = Pipeline(cfg, run_dir, dry=a.dry_run)
    wanted = ORDER if a.cmd == "all" else [a.cmd]

    rc = 0
    try:
        for name in wanted:
            print(f"\n===== {name} =====")
            t0 = time.time()
            rc = STEPS[name](pl)
            print(f"===== {name} done (exit {rc}, {time.time() - t0:.1f}s) =====")
            if rc != 0 and name in ("preflight", "compose"):
                print(f"{name} failed (exit {rc}); stopping. "
                      f"Earlier stages are intact; fix and re-run.")
                break
    except KeyboardInterrupt:
        print("\ninterrupted -- state saved; re-run with --run "
              f"{run_dir.name} to resume")
        rc = 130
    finally:
        pl.close_engine()
        lock.release()
    return rc


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
