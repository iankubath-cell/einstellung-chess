einstellung-chess

A verification pipeline for generating and validating Einstellung-style chess positions — positions where a familiar, playable solution traps the solver into overlooking a superior, less obvious alternative.

Named after the Einstellung (set) effect: the tendency for prior experience to blind a solver to a better solution, because a well-known pattern fires first and monopolises attention. See Bilalić, McLeod & Gobet (2008), "Why good thoughts block better ones: The mechanism of the beneficial Einstellung (set) effect", Cognition 108(3) — (confirm volume/page numbers against the journal record).
The property being engineered

Every position in the canonical set must satisfy all of the following:

    Same first move for both solutions — the solver's choice is not where the fork happens.
    Both solutions force checkmate against best defence.
    The familiar solution is valid but slower — typically a smothered mate in 5.
    A superior solution exists — typically mate in 3 — and is missed because the familiar pattern dominates.
    The familiar line is forced, not merely playable: it must hold against every legal defensive reply, not just one cooperative branch.

Condition 5 is where naive generation fails. A line can replay perfectly in SAN and still be refuted by a defence the generator never tried.
Verification pipeline

Nothing enters the canonical set without passing every gate below. The pipeline — not any model, author, or reviewer — is the authority.
Layer	Gate	What it proves	Runtime
1	Replay gate	SAN sequences replay legally from the FEN and terminate in #	milliseconds
2	Engine gate	Stockfish (depth 26–28, MultiPV ≥ 3) reports the expected #+N at the root	seconds
3	Tree gate	Every legal defensive reply after the shared first move leads to forced mate within budget	minutes/position
4	Falsification controls	Mutations that should break the claim actually do	seconds

Layer 4 matters most. A test that cannot fail proves nothing. Each load-bearing claim is paired with negative controls — removing a guarding bishop, freeing a flight square, adding a defender to the mating square — and the claim is only accepted if the controls die as predicted.
Known failure modes
Failure mode	Detected by	Documented instance
Instant mate shortcut exists	Enumerate all first moves for mate-in-1/2	Greek-gift candidate: 1.Qxh7#
Line replays but a defence refutes it	Tree gate over all replies	Old twin: Nxe6 refutes the queen sacrifice
Shorter line exists but isn't forced	Engine root eval must be exactly #+N	Extinction f6: mate-in-4 leak
Repair breaks the familiar line	Tree gate on the familiar branch	Twin f6+f8N: knight defends e6
Stale FEN under a current label	Failure signature names an impossible piece	Twin v3 run reported Nxe6 in a position with no knight

The last row is the reason for the design rule below.
Canonical positions

FEN is the primary key. Labels are for humans. Any script, document, or review must quote the FEN alongside the ID. If a label and a FEN disagree, the FEN wins and the label is corrected.
ID	Name	Side to move	Status
C1	Critical (Bilalić reconstruction)	White	✅ Verified
C2	Mirror (queenside)	White	✅ Verified
C3	Extinction twin v3 (Ra8)	White	⚠️ Tree gate passed; engine root eval pending
S1	Smothered family, kingside	Black	❌ Untested
S2	Smothered family, queenside	White	✅ Tree gate passed
S3	Smothered family, queenside	Black	✅ Tree gate passed

Machine-readable definitions, including FENs, move sequences, and per-position status detail, live in positions/canonical.json.
Open verification items

    C3 — engine root eval must be exactly #+5 with no mate-in-4 leak. The tree gate proved the familiar line is forced; it says nothing about whether a faster mate exists.
    S1 — requires the colour-aware tree gate (score.pov(attacker), not score.white()). Last position with no test of any kind behind it.
    Both branches — most runs exercise one branch per position. Full verification needs the short and familiar lines gated independently.
    Defence-enumeration counts for S1–S3 (recorded as 33 / 26 / 27) — the load-bearing claim that every legal reply permits mate in 1. Prime target for the falsification suite.
    Kh8 dispute — an unresolved disagreement over one defensive reply; formally open.

Graveyard

Documented failures are kept, not deleted. Each records a cause of death and the lesson extracted.
ID	Name	Cause of death	Lesson
G1	Greek-gift candidate	1.Qxh7# is mate in 1	Enumerate all first moves before anything else
G2	Early generated candidate	No forced mate anywhere (eval +8.99)	Replay check catches "no mate" cheaply
G3	Extinction f6 (leaky)	Mate-in-4 leak	Root eval must be exactly the target #+N
G4	Twin f6+f8N	f8-knight defends e6; Nxe6 refutes	No piece satisfied occupancy and non-defence simultaneously

Full FENs are in positions/canonical.json under graveyard.
Repository layout

einstellung-chess/
├── README.md
├── LICENSE                     # GPL-3.0-or-later
├── requirements.txt
├── positions/
│   ├── canonical.json          # verified + pending positions (data, not code)
│   └── graveyard.json          # documented failures
├── scripts/
│   ├── load_positions.py       # validates IDs, parses FENs, single source of truth
│   ├── engine_gate.py          # layer 2: root eval, MultiPV, known-line replay
│   ├── forced_mate_gate.py     # layer 3: tree gate over all defensive replies
│   ├── falsification_controls.py  # layer 4: Popperian negative controls
│   ├── batch_test_fens.py      # batch replay and classification
│   ├── fen_tool.py             # ASCII board rendering for eyeballing
│   └── analyze_position.py     # ad-hoc single-position analysis
├── docs/
│   ├── METHODOLOGY.md          # why each gate exists; failure-mode catalogue
│   ├── AUDIT-TRAIL.md          # provenance of every position and claim
│   └── OPEN-QUESTIONS.md       # unresolved disputes, with both sides stated
└── tests/
    └── test_canonical.py       # pytest wrapper; fast gates run in CI

Design rules

    Positions are data, not literals. Scripts must read FENs from positions/*.json. Hard-coded FENs in script bodies caused a stale-input failure that cost a full debugging cycle — the run tested a superseded position under a current label and reported a refutation naming a piece that no longer existed.
    FEN is the primary key. IDs are conveniences and may be renumbered; FENs may not silently change.
    No model output is evidence. Generated candidates and claimed analyses enter the audit trail as hypotheses. Only the local pipeline confers verification.
    Tests must be able to fail. Any claim shipped without a negative control is marked as unverified, however plausible it looks.
    Failures are archived, not erased. The graveyard is a deliverable.

Getting started

Requires Python 3.9+ and a Stockfish binary.

pip install -r requirements.txt

# Point at your Stockfish build
export STOCKFISH_PATH=/path/to/stockfish        # Linux/macOS
set STOCKFISH_PATH=C:\path\to\stockfish.exe     # Windows cmd

python scripts/engine_gate.py
python scripts/forced_mate_gate.py
python scripts/falsification_controls.py

Exit codes are CI-friendly: 0 on success, 1 if any gate fails.

requirements.txt:

chess>=1.10

Stockfish is not vendored. Install it separately and point STOCKFISH_PATH at it — see the licence note below.
Continuous integration

Recommended split:

    On every push — replay gate and falsification controls. Fast, deterministic, no engine binary required for the replay portion.
    Nightly or manual — engine gate and tree gate. Minutes per position; depth 28–34 is expensive.

Licence

GPL-3.0-or-later.

This project depends on python-chess, which is licensed GPL-3.0-or-later, and drives Stockfish, also GPL-3.0-or-later. Because python-chess is imported directly, GPL-3.0 for this repository is the straightforward, obligation-compatible choice. Stockfish is invoked as a separate process via UCI and is not redistributed here.

If you redistribute Stockfish binaries alongside this code, GPL-3.0 requires you to include the licence and either the corresponding source or a pointer to it.
Provenance

Positions were generated by a multi-model ensemble acting as independent consultants, with a local test harness as the sole arbiter of truth. Consultant outputs were treated as hypotheses throughout and cross-checked against the pipeline; several were rejected. Contributions are recorded in docs/AUDIT-TRAIL.md by claim and by test result rather than by model reputation — quality varied by question, not by source.
Limitations

    Depth-limited engine search is not proof. #+N at depth 34 is strong evidence, not a theorem.
    The tree gate enumerates legal replies, not reasonable ones. A defence that loses instantly still counts and still must be handled.
    Defence-enumeration counts for the smothered family are asserted, not yet independently reproduced.
    Positions are composed for pedagogical demonstration of the Einstellung effect. No claim is made that they are novel relative to published study material.
