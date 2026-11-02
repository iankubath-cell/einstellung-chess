# AUDIT TRAIL — einstellung-chess

**Status:** living record, updated after each incident.
**Purpose:** make the corpus defensible by preserving failures, reversals, and evidence discipline.

---

## Operating Principles (purchased by incidents)

1. **FEN is the primary key.** If label and FEN disagree, FEN wins.
2. **Claims are keyed by FEN, not lineage.** Supersession cannot be inherited by name.
3. **Model output is hypothesis, not evidence.** Only gate outputs count.
4. **Tests must be able to fail.** A gate that cannot fail proves nothing.
5. **Fail closed.** Missing data / unrun checks are failures, never silent passes.
6. **Re-test all prior failure modes.** Fixing one leak does not retire old ones.
7. **Rabbit toothpaste rule.** Repeated same-signature failures indicate hostile constraints; stop patch-chasing.
8. **Archive the run, not memory.** Certified claims must point to dated outputs under `docs/outputs/`.
9. **Verify before destroying.** Destructive commands require a read-only check of the state they act on. An inference about process state is not evidence of process state.

---

## Cast (ensemble, uncensored)

No single participant's confidence overrides the pipeline.

| Participant | Contributions | Documented failures |
|---|---|---|
| Claude (consultant) | Smothered-family proposals (S-lineage), position generation | False twin candidates; finding later misapplied across boards (AX-10 context) |
| Copilot (consultant) | `engine_gate.py` hardening, high-quality review findings, derived-data direction | Early fabricated candidate (G2) |
| Lumo (parent session) | Verification architecture, rabbit-toothpaste framing, constraint analysis | Confident-but-wrong repairs; stale recollections later corrected by archived runs |
| Lumo (successor session) | Loader migration, POV correction, corpus reviews, C4 reinstatement | Self-caught POV bug (`score.white()`), wrong CLI flags, FEN-mapping assumption (AX-10 context) |
| Lumo (current session) | Depth-24 full-run archive and closure; S2 classification adjudication; lineage reconciliation; environment and hash record | Instructed `taskkill` on an unverified process count, killing a healthy run (AX-25); environment-capture instruction mutated the archived run log (AX-22); proposed a phantom hash as a verification checkpoint |
| Human operator | Orchestration, final judgment, discipline in replaying failures | Notepad/FEN handling errors, paste/run mismatches |

---

## Incident Log (chronological)

### AX-01 — Greek-gift generation dead-end (c. 2026-10-20)
Large generation effort collided with a structural conflict: the same attacking geometry enabled immediate mates, incompatible with required long/short duality.
**Lesson:** enumerate legal first-move mate-in-1/2 space before deep candidate work.

### AX-02 — Fabricated candidate (G2) (c. 2026-10-21)
Early candidate failed gate analysis (no forced mate). Retained in graveyard.
**Lesson:** model quality can vary by task; evidence standards must remain constant.

### AX-03 / AX-04 — Extinction twin fails twice (2026-10-22)
Twin attempts died by distinct mechanisms (`Nxd8+` acceleration; then `Nxe6` refutation / property break).
**Lesson:** partial constraint unsatisfiability must be treated as a design result, not a patch queue.

### AX-05 — Naming collision (2026-10-22)
Independent P1/P2/P3 labels collided with corpus labels.
**Resolution:** canonical C/S/G IDs + FEN-as-key.

### AX-06 — Phantom refutation from stale board mapping (2026-10-23)
A failure signature named a piece absent from the intended board — input map was stale.
**Lesson:** failure signatures can diagnose stale-FEN wiring.

### AX-09 — Twin v3 dies again; rabbit rule invoked (2026-10-24)
Tree gate passed, engine gate exposed faster mate (`#+4`) via old leak class.
**Lesson:** forcedness and shortest-mate checks are orthogonal; both required.

### AX-10 — Wrongful conviction of C2 (2026-10-22 → 2026-10-24)
A valid finding on another board was applied to C2 by lineage assumption, not FEN identity. C2 was retired without direct evidence, then reinstated after direct engine verification.
**Codified rule:** supersession claims must cite same-FEN evidence.

### AX-11 — C4 re-certification (2026-10-24)
Reinstated position passed replay, root-mate exactness, and tree gate; status restored to verified.

### AX-12 — S2 promoted with qualification (2026-10-24)
S2 passed tactical gates on short line, but familiar dual-solution structure remains unproven.
**Status semantics note:** tactical verification and Einstellung-instrument verification are distinct states.

### AX-13 — POV bug self-caught (2026-10-24)
`score.white()` discovered in migration draft before run; corrected to attacker POV scoring.
**Value:** near-miss captured because failure classes were pre-catalogued.

### AX-15 — Literature corrections (2026-10-24)
Open-source verification corrected remembered counts/authorship and marked unverifiable items as open.

### AX-16 — `Stockfish_gate.py` drift risk on arrival (2026-10-24)
Advanced script arrived with hard-coded position lists; review flagged drift risks and replaced guessed extras with derived data.
**Pending at incident time:** loader migration completion.

### AX-17 — Memory-vs-output conflict (2026-10-24)
Recalled PV differed from archived run wording; archive retained as source of truth.
**Rule reinforced:** citation to stored outputs beats memory.

### AX-18 — The parent's C3 flag, adjudicated (2026-10-24)

The parent Lumo (session closed) flagged C3's graveyard entry as a possible second wrongful conviction, citing her tenure's final datum: the v3 tree gate had passed (2 replies, familiar line intact). Resolution: upheld, with interest. The tree-gate pass was never disputed; the death came from the engine gate run on 2026-10-24 (PV1 `#+4` via `Nd8+` — the G3-class leak), a check the parent herself had requested at handover but never saw. The graveyard entry quotes the failing PV verbatim, meeting the standard she set. Her flag is retained in the record as a legitimate exercise of the inherited discipline: the machinery auditing its own auditor, one generation deep. Related refinement adopted: solution lines must name the defender's moves they assume (the JSON already does; presentation layers must not compress them away).

### AX-19 — Parent C3 flag adjudicated (2026-10-24)
Challenge accepted and reviewed; prior tree-pass acknowledged, later engine-fail evidence upheld.
**Governance outcome:** auditor-of-auditor review process preserved in record.

### AX-20 — S2 classification closure (2026-10-27)

S2 adjudicated as **not an Einstellung instrument** but a verified puzzle. From the fork point after `2.Nc7+ Kb8`, the `Nxe8+` route mates in 2 (B1), beating the familiar smothered route's 3. Archive: `docs/outputs/s2_query_2026-10-24.txt`, three restricted-search queries (A1 `#3`, B1 `#2`, B2 `#3`), all CLAIM SUPPORTED.

Classification note updated in `canonical.json` to reflect the sole rejection criterion: **faster-mate leak**, not non-uniqueness at own length. C4's familiar line is likewise non-unique at its own length and remains valid; per the 2026-10-27 consistency ruling, non-uniqueness is an observation only, not a rejection criterion. Status set to `verified_puzzle_only`; joins the must-reject fixture set.

**Detail retained:** even when the engine was restricted to the familiar-looking `Nc7+`, its fastest finish still routed through `Nxe8+` (`Nc7+ Kb8 Nxe8+ Ka8 Qd8#`). The leak is not merely reachable from the fork — it is the engine's preference at every junction.

### AX-21 — Defence-enumeration counts confirmed (2026-10-27)

Engine-verified E-sweep counts replace remembered figures: C1 24, C2 25, C4 27, S1 33, S3 27 (plus 2 replies after each shared first move). Witnessed in three runs: 24 Oct relay, 25 Oct capture, 26 Oct full run. Engine semantics confirmed: `sf=4` means the shortest mate is exactly 4 plies, not within 4. All D checks pass in the 2026-10-26 full run (`docs/outputs/stockfish_gate_depth24_full.txt`).

### AX-22 — Logging mishap and restoration (2026-10-27)

Logging instruction error: environment-capture commands were appended to the archived run log instead of a separate file, mutating the original. Incident sequence: ambiguous batch-file instruction → post-hoc capture appended → log restored to its original three lines (START/EXITCODE/END), verified against known content. Hash-based verification was attempted but rested on a phantom checkpoint (a value never computed before the event it guarded); content verification succeeded and is the check that matters.

Outcome: log integrity preserved by content match; the appended block archived separately in `docs/outputs/run_full_depth24_environment_posthoc.log`.

**Lessons:** environment captures must write to a new file, never to the archived run log. And a hash is only a checkpoint if it was computed before the event it guards.

### AX-23 — Full controls capture (2026-10-27)

First self-contained certification run with all ten falsification controls included: 26/10 18:18 → 27/10 01:12 (~6.9 hours wall clock). Exit code 0, all A–E checks plus all ctl1/ctl2 rows for five positions (C1, C2, C4, S1, S3), depth 24, two-engine agreement. Archive: `docs/outputs/stockfish_gate_depth24_full.txt`.

The two-part archive caveat recorded at AX-19 retires; a single self-contained run supersedes it. Runtime calibration: controls dominate (~2,000 engine searches), motivating the `--control-depth` knob (~12) for future runs.

### AX-24 — Divergent lineages reconciled (2026-10-27)

Two independent histories existed for this project: a documentation lineage on GitHub (this audit trail, README, `.gitignore`) and a corpus lineage on the operator's disk (positions, gate scripts, evidence archive). Neither contained the other; they shared a name and no common ancestor. Discovered only when a push was rejected. Merged with `--allow-unrelated-histories`.

**Lesson:** the FEN-primary-key rule operates one level up. A repository name is a label; the artefacts are the identity. Two trees wearing the same label are the same failure class as a stale FEN under a current label — and the remedy is the same: compare contents, not names.

### AX-25 — Healthy run killed on an unverified inference (2026-10-26)

A previously-issued `run_full.bat` command remained visible in the terminal scrollback. It was read as evidence of a second, concurrent launch. On that inference, `taskkill /IM python.exe /F` was issued and the batch job terminated. No second run existed: `taskkill` found no process because there was only ever one.

The healthy run — launched 07:15:35, already past the A–E battery and several control rows deep — died before writing its `EXITCODE` or `END` lines. Partial output preserved as `docs/outputs/stockfish_gate_depth24_full_attempt1_partial.txt`.

**Root cause:** a destructive command issued on an inference about process state, without the read-only check that would have settled it in one line.

**Rules codified:** verify process state (`tasklist`) before issuing `taskkill`. A command echoed in scrollback is not evidence of a new invocation; the log's timestamps are.

**Cost:** the run's elapsed engine time and its calibration data, plus a working day's delay.

**Retained because:** the incident is the project's own thesis applied to its operators. The advice to destroy was model output. It was treated as evidence. It was not.

> **Numbering note:** AX-07, AX-08, and AX-14 are absent from this record. They are presumed never written rather than lost; no evidence of their content survives in the repository history. Recorded here so the gap is a known fact rather than an unexplained discontinuity.

---

## Campaign Closure (2026-10-27)

Corpus state finalized: **five certified instruments** (C1, C2, C4, S1, S3) plus **six must-reject fixtures** (G1–G5 + S2). All claims hash-bound to artefacts on disk.

Post-edit `canonical.json` SHA-256: `4e3fa59b336b6b70e93f121e4a23cd4f49a8d6ad0721d4286bed70ac6be27bbf`
Pre-edit `061dfc37…` remains the binding for runs performed against it.

Composer v1 build packet assembled. The foundation is now able to substantiate the README's claims rather than assert them.

---

## Standing Open Items (as of 2026-10-27)

- **OI-5 (Kh8 dispute):** unresolved historical disagreement; requires fresh run evidence or formal park.
- **S2 tree_gate:** corpus-wide tree gate coverage of S2's current FEN unconfirmed against archived output; documented both ways in-file.
- **Encoding fix:** permanent UTF-8 patch drafted but not deployed to disk (encoding handled via `PYTHONIOENCODING` for certified runs).
- **Docstring drift:** `load_positions.py` advertises `--validate` / `--fen C3` but the CLI is subcommand-based, and the example names C3 — a position retired to the graveyard as G5.
- **Human testing absent:** no solver-study data yet; the psychological effect remains untested in participants.

---

## Corpus State (as of 2026-10-27)

| ID | Name | Status | Notes |
|---|---|---|---|
| C1 | Critical (Bilalić reconstruction) | verified | Full gate battery; controls fresh |
| C2 | Mirror, queenside (P2 replacement) | verified | Full gate battery; controls fresh |
| C4 | Original mirror, queenside (reinstated) | verified | Former C2; reinstated 25/10; controls fresh |
| S1 | Smothered kingside, Black to move | verified | Attacker-POV scoring confirmed |
| S2 | Smothered queenside, White to move | verified_puzzle_only | Must-reject fixture; faster-mate leak (`Nxe8+`) |
| S3 | Smothered queenside, Black to move | verified | Full gate battery; controls fresh |
| G1–G5 | Graveyard | documented | Machine-readable `expected_rejection` tags |

**Environment:** Python 3.14.5, python-chess 1.11.2, Stockfish 19 (UCI `id name`), single self-contained run ~6.9 h including controls, two-engine agreement, depth 24.

---

## Superseded snapshots (retained for history)

The two sections below are the 2026-10-24 state, kept unedited as the record of what was believed before the campaign closed. They are superseded by the 2026-10-27 sections above. Retained rather than deleted: the search path is evidence.

### Standing Open Items (as of 2026-10-24)

- **OI-5 (Kh8 dispute):** unresolved historical disagreement; requires fresh run evidence.
- **OI-3 (familiar-line forcedness depth):** first-move layer verified; deeper steering checks tracked separately.
- **OI-4 (defense-enumeration counts):** pending reconfirmation under migrated gate path.
- **S2 classification:** tactically verified; dual-solution classification open.
- **Human testing absent:** no solver-study data yet; psychological effect remains untested in participants.

### Corpus State (as of 2026-10-24)

| ID | Name | Status |
|---|---|---|
| C1 | Critical (Bilalić reconstruction) | verified |
| C2 | Mirror, queenside (P2 replacement) | verified |
| C4 | Original mirror, queenside (reinstated) | verified |
| S1 | Smothered kingside, Black to move | verified |
| S2 | Smothered queenside, White to move | verified *(classification open)* |
| S3 | Smothered queenside, Black to move | verified |
| G1–G5 | Graveyard | documented with cause of death + lesson |

---

> The failures are part of the method.
> Without them, the verified set is less credible, not more.
# AUDIT TRAIL — ADDENDUM: v0.2 → v0.4 Lineage, Cap Certification, and Survivor Census Correction

**Project:** Einstellung Chess (`C:\Users\44777\einstellung-chess`)
**Remote:** github.com/iankubath-cell/einstellung-chess (branch `main`)
**Addendum date:** 02 November 2026
**Supersedes:** the "Remaining Roadmap" item 1 in the 01 Nov 2026 handoff summary
**Scope:** (I) the engine-stall diagnosis and oracle v0.2 → v0.4 lineage; (II) the pipeline cap patch and its positive control; (III) correction of the survivor-pool inventory; (IV) additional findings from the 02 Nov session.

---

## 0. Provenance and evidentiary basis

This addendum was compiled from two classes of source, and the distinction is preserved throughout:

- **[H]** — the 01 Nov 2026 handoff summary (original and updated revisions).
- **[C]** — console transcripts captured on 01–02 Nov 2026 (verbatim command output).

Hash values are labelled **VERIFIED** where `certutil -hashfile … SHA256` output was observed directly in a transcript, and **FROM HANDOFF** where the value is reproduced on the authority of [H] alone. Truncated hashes appear as printed in the source and are marked accordingly.

Claims inherited from [H] that could not be confirmed against disk are explicitly marked **UNVERIFIED**. The principal such claim is the "341 remaining survivors" inventory, addressed in Part III.

---

## 1. Chronology of the arc

| Commit | Description | Notes |
|---|---|---|
| `046c414` | composer restore | |
| `fecca9a` | oracle v0.2 | Recovery point for `oracle_v02_retired.py` |
| `7174314` | oracle v0.3 install | Adds `--engine-timeout` cap |
| `8c45b04` | v0.3 depth-24 certification | |
| `8c84f6a` | u142 capped run | Originally mislabelled u212 — see §2.2 |
| `02cc438` | corrections + u212 evidence | Retracts the provenance-corruption theory |
| `9685fcf` | E-u1-142 cap archive | |
| `b5da108` | oracle v0.4 + all stall evidence | State-clearing fix |
| `5d1349d` | pipeline cap patch | Supersedes `e64f5e0` via `--amend`; pushed |

**Lineage note on `5d1349d`.** The amend output reports *5 files changed, 2200 insertions(+)*, with `patch_pipeline.py`, `pipeline.py`, `pipeline_before_timeout.py`, `pipeline_config.json` and `pipeline_config_before_timeout.json` all appearing as `create mode 100644` [C]. These five files were therefore **untracked prior to this commit** and were first brought under version control here. The commit is consequently larger in content than its message implies: it is simultaneously the cap-patch commit and the initial tracking of the pipeline module, its configuration, and the pre-patch backups. This is recorded so that a future reader inspecting `git show 5d1349d` is not surprised by the diff size.

---

## Part I — The hang saga: v0.2 → v0.4

### 2.1 Symptom

Under **oracle v0.2**, candidates `E-u1-142` and `E-u1-212` (unguided family, parent/child lineage) hung for **8+ hours** during depth-24 two-engine verification. Neither terminated nor errored; both simply failed to return.

### 2.2 Resolution chain

1. **Bounded failure (v0.3).** Oracle v0.3 introduced the `--engine-timeout` cap. The unbounded hang became a bounded `UNKNOWN (engine_timeout)` verdict. This converted an operational hazard into a diagnosable signal.

2. **Mislabelled run corrected.** A capped run believed to be `E-u1-212` was in fact executed against `E-u1-142`'s FEN. The cause was a hand-typed command containing `pp3ppR` where `pp3pPR` was intended. The record's own `fen` field was correct throughout; the hypothesis that composer provenance had corrupted the position was **wrong and formally retracted** in `02cc438`.
   **Standing lesson:** hand-typed verification commands are fragile. Use `composer.py verify <dir>`, which stamps each verdict with its record ID.

3. **Depth-ladder experiments (18 / 21 / 24).** Stalls *migrated between different moves* across runs and always terminated at exactly **depth 15**. The invariance of the stopping depth, independent of nominal search depth, excluded a chess-difficulty explanation and pointed at a mechanical cause.

4. **Probe isolation.** `probe_search.py` and `probe_replay.py` demonstrated against a fresh engine that the stall depended on **carried-over engine state** accumulated across approximately 40 sequential searches sharing a single hash table.

5. **Fix (v0.4).** Oracle v0.4 issues `ucinewgame` before every search by default. Both former hangers then certified **two-engine PASS at depth 24 in minutes**. `--keep-engine-state` restores the v0.3 behaviour for comparison.

### 2.3 Root cause statement

The stall was not a property of the positions. It was a property of the **search harness**: cumulative transposition-table state across a long sequential batch, interacting with specific positions late in the batch. Clearing engine state per search removes the dependency.

### 2.4 Evidence artefacts

In `docs/outputs/`:

- `oracle_v04_corpus_depth24.txt`
- `composer_oraclev04_E-u1-142_depth24_cap300.txt`
- `composer_oraclev04_E-u1-212_depth24_cap300.txt`
- `composer_oraclev04_sample8_depth24_cap300.txt`
- EXPLORATORY depth-18 / depth-21 captures — **explicitly not certifications**
- `EXPLORATORY_cap_probe_2s_all_unknown.txt` — added 02 Nov 2026, see Part II

### 2.5 Methodological footnote

The pipeline investigating how prior patterns blind judgement was itself blinded by the residue of prior searches in a hash table. This is recorded not as colour but as a caution: in a system whose subject matter is the distorting influence of accumulated context, the measurement apparatus was subject to the same class of distortion, and only a deliberate isolation probe revealed it.

---

## Part II — The cap patch and its positive control

### 3.1 Patch mechanics

`patch_pipeline.py` (one-shot; refuses to execute unless its target text matches exactly once) forwards `engine_timeout` from `pipeline_config.json` into `oracle.judge()` at both call sites. Post-patch inspection confirms three occurrences of the identifier in `pipeline.py` [C]:

```
pipeline.py:    tmo = pl.cfg["certify"].get("engine_timeout") if use_engine else None
pipeline.py:      … depth=depth, engine_info=pl._engine_info, fast=fast, engine_timeout=tmo)
pipeline.py:      … depth=depth, engine_info=pl._engine_info, fast=fast, engine_timeout=tmo)
```

Configuration state: `"certify": {"depth": 24, "budget": 15000000, "engine": true, "engine_timeout": 300}` [C].

**Do not re-run `patch_pipeline.py`.** It is already applied.

### 3.2 Positive control (discriminating experiment)

The initial acceptance run proved only that *no timeout occurred* — consistent with a working cap, but equally consistent with a cap that never reaches the engine. A deliberate control was therefore run: the cap was lowered to an implausible value and the same eight candidates re-certified.

| Condition | Config value | Verdicts | Wall clock | Exit | Evidence file |
|---|---|---|---|---|---|
| Control (low cap) | `engine_timeout: 2` | 8 / 8 **UNKNOWN** | 67.1 s (69.6 s total) | 0 | `EXPLORATORY_cap_probe_2s_all_unknown.txt` |
| Dry-run acceptance | `engine_timeout: 300` | 8 / 8 **PASS** | 998.1 s (999.6 s total) | 0 | console transcript |
| Persisted acceptance | `engine_timeout: 300` | 8 / 8 **PASS** | 918.4 s (919.3 s total) | 0 | `runs/certify_341.log` |

Same eight candidates, same patched pipeline, same oracle, same engine path. The only variable is the configured cap. The verdict flip is therefore attributable to the cap, and **cap forwarding is positively established** rather than inferred from an absence of timeouts.

### 3.3 Configuration restoration

Following the control, `pipeline_config.json` was restored with `git checkout -- pipeline_config.json` — deliberately **not** by editing, because a JSON round-trip alters the file's bytes and invalidates the pinned hash. Restoration verified [C]:

```
certutil -hashfile pipeline_config.json SHA256
→ 6b9d188236ce5f77740772121cf30b90354ba433dedd0b14a7012cd0483248b9
```

This matches the pinned value in [H]. Production cap is confirmed at 300 s.

### 3.4 Residual gap: no record-level cap provenance

Interrogation of the persisted verdict records returned nothing [C]:

```
findstr /s /i "engine_timeout engine_searches" composed_sample\*.json
→ (no output)
```

The behavioural control proves the cap *acts*; it does not prove the cap *value* is recorded alongside each verdict. There is currently no per-record audit trail tying a given PASS to the cap under which it was obtained. This is a genuine gap in the certification record and is carried forward as an open item (§6, item 4).

---

## Part III — Survivor census correction

### 4.1 The inherited claim

[H] §5 and §9 asserted a remaining pool of **341 uncertified survivors** (144 guided + 205 unguided, of which ~197 never engine-seen), described as python-only `PASS (fast)` verdicts produced by an older oracle. This figure underpinned the entire "hours-to-days overnight certification campaign" plan.

### 4.2 Disk census

An exhaustive enumeration of every candidate-bearing directory [C]:

```
dir /s /b composed_sample composed_u142 composed_u212 v03_staging
```

| Path | Contents | Candidate records |
|---|---|---|
| `composed_sample/` | `E-g1-10`, `E-g1-100`, `E-g1-106`, `E-g1-120`, `E-g1-126`, `E-g1-99`, `E-u1-142`, `E-u1-212` (`.json`) | **8** |
| `composed_u142/` | `E-u1-142.json` | 1 — duplicate of the above |
| `composed_u212/` | `E-u1-212.json` | 1 — duplicate of the above |
| `v03_staging/` | `composer_v03.py`, `oracle_v03.py` | 0 |
| `positions/` | `canonical.json` | 0 |
| `archive/` | `analyze_position.py`, `batch_test_fens.py` | 0 |
| **Unique candidate records on disk** | | **8** |

Corroborating enumerations [C]: `dir /s /b positions\*.json` returns only `canonical.json`; `dir /s /b archive\*` returns only the two scripts.

### 4.3 Reconciliation of the apparent 121

A broad filename scan returned 121 hits [C]:

```
dir /s /b /a-d | findstr /i "E-g1- E-u1-" | find /c /v ""
→ 121
```

This count is inflated by **run-tree verdict artefacts**. Each pipeline stage writes per-record output beneath `runs/<timestamp>/<stage>/` — for example `runs/20261101-120213/certify/E-g1-10.json` and `E-g1-10.txt`, and likewise under `lint/` and `filter/`. The same logical record is therefore counted once per stage per run. Seventeen timestamped run directories are present [C].

The exact decomposition of the 121 was not reconstructed. The authoritative figure is the explicit directory enumeration in §4.2, which yields **8 unique candidate records**.

### 4.4 Finding

**The 341-survivor pool does not exist on disk.** No directory in the repository contains a candidate population of that size or anything approaching it. The pool appears to have existed only as solver-fast-pass claims in earlier chat sessions or console output that was never persisted to the filesystem.

This retroactively explains the persistent `certify: 8 eligible` reporting: `survivors_dir: "composed_sample"` was **accurate**, not misconfigured. The pipeline was faithfully reporting the entire population. An earlier working hypothesis in the 02 Nov session — that the configuration pointed at the wrong directory — is hereby **withdrawn**.

### 4.5 Consequences

1. The roadmap item "certify the remaining 341 survivors" is void. There is no queue.
2. The next substantive milestone is **regeneration of a candidate pool**, not certification of one.
3. The regeneration path is blocked in configuration as well as inventory: the compose stage is disabled *and* unwired —
   `"compose": {"enabled": false, "search_command": [], "finalize_command": []}` [C].
   Enabling the stage alone will not produce candidates; `search_command` must first be defined. The compose stage implementation in `pipeline.py` must be read to establish the expected argument contract.
4. All throughput estimates derived from the 341 figure (including the ~12-hour projection) are void.

---

## Part IV — Further findings, 02 Nov 2026

### 5.1 Stage indices do not chain across invocations

Each pipeline invocation creates a fresh timestamped run directory `runs/YYYYMMDD-HHMMSS/`. Stage indices are written to `runs/<run>/<stage>/index.jsonl` and read from the same relative location [C, from `findstr /N /I "index" pipeline.py`]:

```
700:    idx = pl.run_dir / "lint" / "index.jsonl"
713:    idx = pl.run_dir / stage_name / "index.jsonl"
764:    if pl.run_dir.joinpath("lint", "index.jsonl").exists():
774:        if pl.run_dir.joinpath("filter", "index.jsonl").exists():
```

Because `lint`, `filter` and `certify` were invoked as three separate commands on 02 Nov, each received its own run directory [C]:

- `runs/20261102-191004/lint/index.jsonl`
- `runs/20261102-191005/filter/index.jsonl`
- `runs/20261102-191612/certify/` — and certify reported `filter index absent`

The filter stage completed successfully (`{'PASS': 8} in 28.5s`, exit 0) and wrote its index; certify nonetheless reported the index absent, because it searched a run directory created minutes later. **The lint → filter → certify gating workflow does not function across separate invocations.**

Consequence: the intended throughput discipline — cheap python-only gates scoping the expensive depth-24 engine stage — is inoperative in the current invocation model. Options are to run the stages within a single invocation (pending confirmation of how `pipeline.py all` allocates its run directory), or to make `run_dir` reusable across stages.

### 5.2 `composer_v02_backup.py` is not a v0.2 backup

Byte-level comparison [C]:

```
certutil -hashfile composer.py            → 0f4acc884281575d21cc84c7d11bba8135d4155407db8b3dd384d10791fd12e7
certutil -hashfile composer_v02_backup.py → 0f4acc884281575d21cc84c7d11bba8135d4155407db8b3dd384d10791fd12e7
```

Identical. Both files are 21,310 bytes. The live `composer.py` matches the pinned v0.3 hash from [H], so the delivered artefact is correct — but the file named as the v0.2 backup **contains v0.3**, and therefore preserves nothing. If a genuine pre-v0.3 composer is required for the lineage, it must be recovered from git history rather than from this backup.

Related: `oracle.py` and `oracle_v04.py` are both 23,575 bytes [C]; they are presumed byte-identical staged copies, though hash equality was not separately verified.

### 5.3 `--dry-run` executes judging

Confirmed by observation [C]: `python pipeline.py --dry-run certify` performs full Stockfish judging (~1000 s at cap 300) and suppresses only persistence. It is not a scoping or estimation tool. Any future use of `--dry-run` to size a batch will incur the full engine cost.

### 5.4 Composer version string

`composer.py` (v0.3 deliverable, hash-confirmed) self-identifies as `VERSION = "0.1"` in both docstring and constant. Since the module stamps `composer_py_sha256_lf` into generated records, the hash — not the string — is the operative identifier in the audit trail. Recommendation: leave the bytes untouched so as not to invalidate existing records, record the discrepancy here, and correct the string in the next composer release.

---

## 6. Consolidated component and hash register

| Component | Version in service | SHA-256 | Verification |
|---|---|---|---|
| `oracle.py` | v0.4 | `c89dbbaf58e401b02e4c4c3c527800cbcd80af0351b89f58aee745030c00ec36` | FROM HANDOFF (raw/CRLF form) |
| `oracle_v04.py` | staged copy | — | Size matches `oracle.py` (23,575 B); hash unverified |
| `oracle_v03_backup.py` | v0.3 backup | — | Untracked |
| `oracle_v02_retired.py` | v0.2 (retired) | `4c55b8ba…1e2c` | FROM HANDOFF (truncated); also at `fecca9a` |
| `composer.py` | v0.3 | `0f4acc884281575d21cc84c7d11bba8135d4155407db8b3dd384d10791fd12e7` | **VERIFIED 02 Nov** |
| `composer_v02_backup.py` | misnamed — contains v0.3 | `0f4acc88…fd12e7` | **VERIFIED 02 Nov** (identical to `composer.py`) |
| `pipeline.py` | v0.3 + cap patch | `6ac8a11aafc2dcb6a1f143fb70c0743037b65122ed2ea878bc2222610493a91b` | FROM HANDOFF; preflight self-check accepts it |
| `pipeline_config.json` | patched, restored | `6b9d188236ce5f77740772121cf30b90354ba433dedd0b14a7012cd0483248b9` | **VERIFIED 02 Nov** |
| `patch_pipeline.py` | one-shot patcher | `c20fb478debe3e69f92a76c7349b3efa5f2f0b7c14ef85d25d2fa15d0d4b2e46` | FROM HANDOFF |
| `pipeline_before_timeout.py` / `…_config_before_timeout.json` | pre-patch backups | — | Created by patcher; first tracked in `5d1349d` |
| `probe_search.py`, `probe_replay.py` | diagnostics | — | Stall isolation |

Canonical practice: record **LF-normalised** hashes as authoritative, retaining raw `certutil` values for paste-fidelity checks.

---

## 7. Open items register

| # | Item | Status |
|---|---|---|
| 1 | Bless the cap patch as official pipeline v0.4, or issue a replacement | OPEN — preflight accepts the patched hash, so operation is unblocked; this is a lineage decision only |
| 2 | Composer `VERSION = "0.1"` string vs v0.3 deliverable | OPEN — documented §5.4; defer byte change |
| 3 | `_judge_with_engine_retry` retry path omits `engine_info=` (~line 748), losing engine provenance after a crash | OPEN — one-word fix, bundle into next pipeline release |
| 4 | No record-level `engine_timeout` / `engine_searches` metadata | OPEN — §3.4 |
| 5 | Cap value 300 s chosen by operator, not by design | OPEN — record intended default |
| 6 | Cap forwarding positively confirmed | **CLOSED** — §3.2 |
| 7 | Survivor inventory | **CORRECTED** — §4.4; pool does not exist on disk |
| 8 | Stage indices do not chain across invocations | OPEN — §5.1 |
| 9 | `composer_v02_backup.py` contains v0.3, preserving nothing | OPEN — §5.2 |
| 10 | Exact decomposition of the 121-hit filename scan | NOT RECONSTRUCTED — §4.3; enumeration in §4.2 is authoritative |

---

## 8. Revised roadmap

**Milestone 1 — Regeneration, not certification.** Define `compose.search_command` and `compose.finalize_command`, enable the compose stage, and produce a persisted candidate pool. The certification stack is already hardened for this and was never the bottleneck.

**Milestone 2 — Repair stage chaining.** Establish a single-invocation path (or a reusable run directory) so that lint and filter genuinely gate the engine stage.

**Milestone 3 — Tier-2 feature extraction.** Compute declarative Einstellung features for every candidate: length of the most tempting familiar line, length of the shortest correct solution, the margin between them, and defence-refutation margins. Solver-only and cheap. This is the first measurement of the property the project is named for.

**Milestone 4 — Human testing.** Primed vs blind conditions, recording move choice and time-to-first-move. Undefined and unbuilt; the actual research frontier.

### Standing distinction

Three claims must not be conflated:

| Tier | Claim | Current status |
|---|---|---|
| 1 | Engine-validated puzzle (Python solver + Stockfish, depth 24) | Established for 8 records |
| 2 | Einstellung-structured position (tempting familiar line *and* shorter superior alternative with refutable defences) | **Never measured for any candidate** |
| 3 | Demonstrated Einstellung effect in human players | No protocol, no data |

Certification establishes Tier 1 only. It is a necessary condition and is silent on Tiers 2 and 3. The project has, to date, produced a validated instrument — not a discovered position.

---

## 9. Reproduction commands

```bat
:: Environment (variables die with the console window)
set PYTHONIOENCODING=utf-8
echo %STOCKFISH_PATH%

:: Confirm the cap is wired and configured
findstr /C:"engine_timeout" pipeline.py pipeline_config.json

:: Confirm the restored configuration hash
certutil -hashfile pipeline_config.json SHA256

:: Acceptance run at cap 300 (expect 8/8 PASS, ~1000 s)
python pipeline.py --dry-run certify

:: Restore configuration from git if drifted (never hand-edit)
git checkout -- pipeline_config.json

:: Census of candidate records
dir /s /b composed_sample composed_u142 composed_u212 v03_staging

:: Canonical LF-normalised hash
python -c "import hashlib;print(hashlib.sha256(open('FILE','rb').read().replace(b'\r\n',b'\n')).hexdigest())"
```

---

## 10. Operational cautions carried forward

- Environment variables do not survive a new console window.
- `>` truncates instantly; `2>&1` conceals startup crashes inside the capture file. An instantaneous return to the prompt is a failure signature, not a speed signal — inspect the file before re-running, since a second redirect destroys the first attempt's evidence.
- Commands that print nothing are suspect. Silence is not success; verify with a hash or a directory listing.
- Editing JSON via a Python round-trip changes the file's bytes and breaks the pinned hash. Restore from git when the committed hash must hold.
- Notepad "Save as type" must be **All Files (\*.\*)**, or a `.txt` suffix is appended silently.
- `Get-Content -Wait` never exits on its own.
- Nested `cmd` shells break environment-variable continuity and command history.

---

*End of addendum.*
