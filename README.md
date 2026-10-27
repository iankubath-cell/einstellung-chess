# einstellung-chess

A verification pipeline for generating and validating Einstellung-style chess positions — positions where a familiar, playable solution traps the solver into overlooking a superior, less obvious alternative.

Named after the Einstellung (set) effect: the tendency for prior experience to blind a solver to a better solution, because a well-known pattern fires first and monopolises attention. See Bilalić, McLeod & Gobet (2008), "Why good thoughts block better ones: The mechanism of the beneficial Einstellung (set) effect", *Cognition* 108(3).

## The property being engineered

Every position in the canonical set must satisfy all of the following:

1. **Same first move** for both solutions — the solver's choice is not where the fork happens.
2. **Both solutions force checkmate** against best defence.
3. **The familiar solution is valid but slower** — typically a smothered mate in 5.
4. **A superior solution exists** — typically mate in 3 — and is missed because the familiar pattern dominates.
5. **The familiar line is forced, not merely playable:** it must hold against every legal defensive reply, not just one cooperative branch.

Condition 5 is where naive generation fails. A line can replay perfectly in SAN and still be refuted by a defence the generator never tried.

## Verification pipeline

Nothing enters the canonical set without passing every gate below. The pipeline — not any model, author, or reviewer — is the authority.

| Layer | Gate | What it proves | Runtime |
|---|---|---|---|
| 1 | Replay gate | SAN sequences replay legally from the FEN and terminate in `#` | milliseconds |
| 2 | Engine gate | Stockfish (depth 24, MultiPV) reports the expected `#+N` at the root | seconds |
| 3 | Tree gate | Every legal defensive reply after the shared first move leads to forced mate within budget | minutes/position |
| 4 | Falsification controls | Mutations that should break the claim actually do | hours (full corpus) |

Layer 4 matters most. **A test that cannot fail proves nothing.** Each load-bearing claim is paired with negative controls — removing the attacker queen, deriving key-piece sets and removing each in turn — and the claim is only accepted if the controls die as predicted.

Control semantics (per ctl1/ctl2):
- **ctl1** — remove the attacker queen: nothing mates within 3. A real falsification: the claim can fail.
- **ctl2** — derived key-piece set non-empty: the shared move breaks when any key piece is removed. A sanity check: weak positive evidence, not proof.

## Known failure modes

| Failure mode | Detected by | Documented instance |
|---|---|---|
| Instant mate shortcut exists | Enumerate all first moves for mate-in-1/2 | Greek-gift candidate: `1.Qxh7#` |
| Line replays but a defence refutes it | Tree gate over all replies | Old twin: `Nxe6` refutes the queen sacrifice |
| Shorter line exists but isn't forced | Engine root eval must be exactly `#+N` | Extinction f6: mate-in-4 leak |
| Repair breaks the familiar line | Tree gate on the familiar branch | Twin `f6+Ng8`: knight defends e6 |
| Stale FEN under a current label | Failure signature names an impossible piece | Twin v3 run reported `Nxe6` in a position with no knight |

The last row is the reason for the design rules below.

## Canonical positions

FEN is the primary key. Labels are for humans. Any script, document, or review must quote the FEN alongside the ID. If a label and a FEN disagree, the FEN wins and the label is corrected.

| ID | Name | Side to move | Status |
|---|---|---|---|
| C1 | Critical (Bilalić reconstruction) | White | ✅ Verified |
| C2 | Mirror (queenside, P2 replacement) | White | ✅ Verified |
| C4 | Original mirror, queenside (reinstated) | White | ✅ Verified |
| S1 | Smothered family, kingside | Black | ✅ Verified |
| S3 | Smothered family, queenside | Black | ✅ Verified |

**S2** (smothered family, queenside, White) is *not* an instrument: it is a verified puzzle (`verified_puzzle_only`) with a faster-mate leak — from the fork point after `2.Nc7+ Kb8`, the `Nxe8+` route mates in 2, beating the familiar smothered finish in 3. It is retained as a **must-reject fixture**: a position that looks like an Einstellung instrument and is not, preserved so that any future composer or classifier must reject it.

Machine-readable definitions, including FENs, move sequences, per-position status detail, and the graveyard, live in `positions/canonical.json`.

## Must-reject fixture set

Six fixtures, each tagged in `canonical.json` with `expected_rejection`:

- **G1–G5** — the graveyard (below)
- **S2** — `faster_mate_leak`

Any candidate generator or classifier must fail on all six to be considered working.

## Open verification items

- **OI-5 (Kh8 dispute)** — an unresolved historical disagreement over one defensive reply; formally open pending fresh run evidence.
- **S2 tree_gate** — corpus-wide tree gate coverage of S2's current FEN is unconfirmed against archived output; documented both ways in-file.
- **Encoding fix** — permanent UTF-8 patch drafted but not deployed to disk (certified runs used the `PYTHONIOENCODING` workaround).
- **Human testing absent** — no solver-study data yet; the psychological effect remains untested in participants.

## Graveyard

Documented failures are kept, not deleted. Each records a cause of death and the lesson extracted.

| ID | Name | Cause of death | Lesson |
|---|---|---|---|
| G1 | Greek-gift candidate | `1.Qxh7#` is mate in 1 | Enumerate all first moves before anything else |
| G2 | Early generated candidate | No forced mate anywhere (eval `+8.99`) | Replay check catches "no mate" cheaply |
| G3 | Extinction f6 (leaky) | Mate-in-4 leak | Root eval must be exactly the target `#+N` |
| G4 | Twin `f6+Ng8` | g8-knight defends e6; `Nxe6` refuted | No piece satisfied occupancy and non-defence simultaneously |
| G5 | Extinction twin v3 (former C3) | Engine gate found `#+4` via `Nd8+` — the G3-class leak, after its tree gate had passed | Forcedness and shortest-mate are orthogonal; both required |

Full FENs are in `positions/canonical.json` under `graveyard`.

## Repository layout

```
einstellung-chess/
├── README.md                  # this file
├── LICENSE                    # GPL-3.0-or-later
├── .gitignore
├── Stockfish_gate.py          # certification gate battery (A–E + controls)
├── load_positions.py          # validates IDs, parses FENs, single source of truth
├── engine_gate.py             # layer 2: root eval, MultiPV, known-line replay
├── forced_mate_gate.py        # layer 3: tree gate over all defensive replies
├── falsification_controls.py  # layer 4: negative controls (G1 harness)
├── s2_query.py                # restricted-search queries for the S2 adjudication
├── fen_tool.py                # ASCII board rendering for eyeballing
├── verify_seed.py             # seed verification for generation reproducibility
├── testChess.py               # smoke test
├── archive/                   # quarantined drift vectors (documented, kept)
│   ├── batch_test_fens.py     # hard-coded FENs absent from canonical (AX-quarantine)
│   ├── analyze_position.py    # ad-hoc analysis of a non-canonical position
│   └── run_full.bat           # launcher for the full-run certification (kept with evidence history)
├── positions/
│   └── canonical.json         # instruments, fixtures, graveyard (data, not code)
├── docs/
│   ├── AUDIT_TRAIL.md          # incident chronology, cast table, evidence discipline
│   └── outputs/                # dated run archives — the evidence
│       ├── stockfish_gate_depth24_full.txt          # THE certification: A–E + all 10 controls, exit 0
│       ├── stockfish_gate_depth24.txt               # A–E capture (--skip-controls)
│       ├── stockfish_gate_depth24_relayed_copy.txt   # 24 Oct relay (superseded, retained)
│       ├── stockfish_gate_depth24_full_attempt1_partial.txt  # autopsy of the killed run (AX-25)
│       ├── s2_query_2026-10-24.txt                   # S2 adjudication evidence
│       ├── run_full_depth24.log                     # run lifecycle: START/EXITCODE/END
│       └── run_full_depth24_environment_posthoc.log # environment + hashes + engine identity
└── src/                       # legacy directory from early generation (pre-dates loader architecture)
```

## Design rules

1. **Positions are data, not literals.** Scripts must read FENs from `positions/*.json`. Hard-coded FENs in script bodies caused a stale-input failure that cost a full debugging cycle — the run tested a superseded position under a current label and reported a refutation naming a piece that no longer existed.
2. **FEN is the primary key.** IDs are conveniences and may be renumbered; FENs may not silently change.
3. **No model output is evidence.** Generated candidates and claimed analyses enter the audit trail as hypotheses. Only the local pipeline confers verification.
4. **Tests must be able to fail.** Any claim shipped without a negative control is marked as unverified, however plausible it looks.
5. **Failures are archived, not erased.** The graveyard is a deliverable.
6. **Verify before destroying.** Destructive commands require a read-only check of the state they act on; an inference about process state is not evidence of process state.

## Method integrity & audit trail

This corpus is verified by gates, not by model confidence. Every position claim is keyed by FEN (not label/lineage), and every certified statement is reproducible from archived outputs.

**Campaign closure (2026-10-27):**

- Certified instruments: **C1, C2, C4, S1, S3** — five positions
- Must-reject fixtures: **G1–G5 + S2** — six positions
- Single self-contained certification run: 26/10 18:18 → 27/10 01:12 (~6.9 h), depth 24, all A–E checks plus all ten falsification controls, two-engine agreement (python-chess + Stockfish 19), exit code 0
- Defence-enumeration counts, engine-verified across three witnessing runs: C1 24, C2 25, C4 27, S1 33, S3 27
- Post-edit `canonical.json` SHA-256: `4e3fa59b336b6b70e93f121e4a23cd4f49a8d6ad0721d4286bed70ac6be27bbf` (pre-edit `061dfc37…` binds the runs performed against that version)
- Environment: Python 3.14.5, python-chess 1.11.2, Stockfish 19 (`id name` via UCI handshake)

See `docs/AUDIT_TRAIL.md` for the full incident chronology (AX-01 → AX-25), the cast table, and the evidence discipline.

## Getting started

Requires Python 3.9+ and a Stockfish binary.

```
pip install chess
```

Point at your Stockfish build:

```
# Linux/macOS
export STOCKFISH_PATH=/path/to/stockfish
# Windows cmd
set STOCKFISH_PATH=C:\path\to\stockfish.exe
```

```
python load_positions.py validate
python engine_gate.py
python forced_mate_gate.py
python falsification_controls.py
```

Exit codes are CI-friendly: 0 on success, 1 if any gate fails.

Stockfish is not vendored. Install it separately and point `STOCKFISH_PATH` at it — see the licence note below.

## Continuous integration

Recommended split:

- **On every push** — replay gate and falsification controls. Fast, deterministic, no engine binary required for the replay portion.
- **Nightly or manual** — engine gate and tree gate. The full certification battery (depth 24, controls included) measures ~7 hours on commodity hardware; see `docs/outputs/run_full_depth24.log`.

## Licence

GPL-3.0-or-later.

This project depends on python-chess, which is licensed GPL-3.0-or-later, and drives Stockfish, also GPL-3.0-or-later. Because python-chess is imported directly, GPL-3.0 for this repository is the straightforward, obligation-compatible choice. Stockfish is invoked as a separate process via UCI and is not redistributed here.

If you redistribute Stockfish binaries alongside this code, GPL-3.0 requires you to include the licence and either the corresponding source or a pointer to it.

## Provenance

Positions were generated by a multi-model ensemble acting as independent consultants, with a local test harness as the sole arbiter of truth. Consultant outputs were treated as hypotheses throughout and cross-checked against the pipeline; several were rejected. Contributions are recorded in `docs/AUDIT_TRAIL.md` by claim and by test result rather than by model reputation — quality varied by question, not by source.

## Limitations

- Depth-limited engine search is not proof. `#+N` at depth 24 is strong evidence, not a theorem.
- The tree gate enumerates legal replies, not reasonable ones. A defence that loses instantly still counts and still must be handled.
- Positions are composed for pedagogical demonstration of the Einstellung effect. No claim is made that they are novel relative to published study material.
- The psychological claim is untested: no human solver data has been collected against this corpus.
