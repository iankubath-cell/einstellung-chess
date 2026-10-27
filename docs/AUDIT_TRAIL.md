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
