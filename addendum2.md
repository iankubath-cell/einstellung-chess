# AUDIT TRAIL — ADDENDUM II: Weak-Form Breakthrough, Tooling Findings, Cross-Stack Adjudication, and First Tier-1 Estimation



**Addendum dates:** 15–21 November 2026

**Numbering:** AX-26 → AX-32, continuing the incident-log discipline (one incident per number).



---



### AX-26 — Weak-form certification: the first definition-born records (2026-11-15)



**Event:** Certification run `20261115-091044` (fresh run dir; `survivors_dir` = `ep_scan_r2`; run transcripts force-committed with the 17 candidate records). ep_gen v0.4 — weak-form probe: entry = mating-optimal move, tempting fork surveyed one ply deeper — produced 17 candidates; **9 PASS at depth-24 two-engine**: the first definition-born weak-form certified records in project history (E-W-1-143 leads: Rh8+ after Kh7, short 2 / familiar 5).



Round 1 context: 57 accepts, zero certifications — **strong-form by construction** (the tempting first move always triggers `alt_first_move_mates`). Deaths structural, not accidental; archived as findings.



Attrition (17 → 9), three findings:

- **FINDING A — zugzwang quiet-mate blindness (3/17).** Checks-only uniqueness survey misses quiet non-checking root mates (E-W-1-156/1-169/1-190). Cure designed for v0.5: exact all-roots table via `oracle.Solver.len_after`.

- **FINDING B — replay dawdle (3/17).** Depth-18 PV replay stalls → `faster_mate_leak` (E-W-2-109/2-121/2-192). Cure: node-by-node solver verification at generation time.

- **FINDING C — engine-vs-solver ±1 disputes fail closed (2/17).** E-W-2-070/2-154. Only agreement is evidence; certification refused both sides.



### AX-27 — The engine-path saga: transcription is a lossy channel (2026-11-15)



`fen_eval.py` failed with engine-not-found under **both** directory spellings while `pipeline_config.json` carried the correct hyphenated path throughout. The assistant rewrote the correct literal wrongly twice from memory; an invisible-character hypothesis died to a `repr()` probe. Origin: the 2026-11-14 handoff document itself carried the wrong spelling — patient zero. Permanent fix: engine defaults read from the config (single source of truth).



**Canonized:** any fact that matters is read from its authority at the moment of use; `repr()` is the only eyeball-free probe of string contents.



### AX-28 — Caption falsified; root-duel trio verified; cross-tool concordance (2026-11-16)



The "Quiet Offer" caption claimed gxh6 refutes Rc8; exhaustive probe: **Rc8 mates in exactly 3** — caption falsified, position reclassified strong-form shadow. The three Base44 library duels verified by three independent exhaustive stacks (chess.js, fen_eval, oracle.Solver), zero disagreements. New texture: "loud-and-empty" checking roots; five-fold quiet tie (later shown structural). All fail only `shared_first_move_broken` — one clause from the certified tier. Evidence: `base44_root_duel.md`.



### AX-29 — Cross-stack adjudication of generated batches; the transcription gauntlet (2026-11-19/20)



`adjudicate_base44.py` v0.1.1 re-proved 20 generated duels with `oracle.Solver`, defense by defense: **20/20 PASS**, all 20 root counts matching chess.js exactly. Concordance now 30 positions, three exhaustive stacks. The session-1 export survived a five-stage transcription gauntlet (missing save → mislabeled copy → zero-byte paste → clipboard captured an instruction block → extension-hidden filenames), bypassed by locating the app's own export on disk. A 32 KB rewrite of this trail then truncated mid-paste and was committed before verification (caught by post-commit probe); repaired by machine assembly from git history. **Canonized:** before transcribing, ask whether the source already exists as a file; assemble large documents from parts; probe before commit, never after.



### AX-30 — Cross-stack adjudication grows; first Tier-1 density measurement (2026-11-21)



The Base44 duel finder's estimation mode ran two seeded universes. **Global** (uniform no-pawn, 8–12 pieces incl. kings; seed 20261121; 4,500 draws): **1 duel in 4,500** — Wilson 0.004–0.126%, factorizing as P(net) 3.9% × P(duel|net) 0.57%; zero truncation; budgets 2,500 ms / 400k nodes (raised after a forensic re-test of 12 unproven draws showed all resolved in ≤1.7 s — the earlier 800 ms clock was the binding constraint, making the advertised node cap dead code; found by autopsy, corrected, and the change is recorded in the run). The single global duel, `3B3N/8/8/8/2R5/2bK4/3b1k2/3Q4 w`, quiet Rg4 = 2 (15 defences, all refuted), Qe2+ = 3 — **cross-stack certified**: oracle.Solver `len_after` total 2 / total 3, 25 nodes, matching chess.js double-verification. First corpus member with no library ancestry — the strongest diversity datapoint to date.



**Local** (one-perturbation draws; seed 777001; 1,000 draws): draw-level 57.7% (54.6–60.7), unique-class 52.6% (48.6–56.6) — interpreted as a **validity measure of basin radius around verified nets**, not a population estimate. Duplicate rate 409/1000 ⇒ the one-step neighborhood is nearly exhausted; deeper local sampling needs mutation chains.



**Open:** the local record's procedure text names the three libraries as seeds, but its strata (18/19/20/24/25 pieces; none in 21–23) match neither the libraries (8, 9, 18 pieces) nor any stated pool — seed provenance unresolved; the material-density confound (local 18–25 vs global 8–12) is therefore uncontrolled. Four loud-fast draws in the unproven re-test show the strict predicate bites even at the desert's edge.



### AX-31 — Budget honesty doctrine (2026-11-21)



An advertised budget that cannot bind (120k nodes behind an 800 ms clock at 40–60k nodes/s) is a false guarantee: the run record stated a node guarantee and delivered a time guarantee. Discovered by re-testing fail-closed rejects rather than trusting them. **Doctrine:** a limit named in a record must be the limit that can actually fire; "unproven" must always name its cause; resource bounds are calibrated against observed throughput, never against intention.



### AX-32 — First Tier-1 density measurement; the estimation arc (2026-11-21)



**The triple** (all seeded, versioned, fail-closed; full checks after the screen experiments below):

- **Global** (uniform no-pawn, 8–12 pieces incl. kings; 4,500 draws): 1 duel / 4,500 = 0.022% [0.004–0.126], factorizing as P(net) 3.9% × P(duel|net) 0.57%. The single hit, `3B3N/8/8/8/2R5/2bK4/3b1k2/3Q4 w` (quiet Rg4, 15 defences refuted; Qe2+ = 3), cross-stack certified (oracle.Solver 25 nodes).

- **Net-local** (one-perturbation draws around heavy nets; 1,000): 57.7% [54.6–60.7] draw-level, 52.6% unique-class — reinterpreted as a *basin-radius validity measure*, not a population estimate.

- **Light-local** (5-seed pool of verified 8–9-piece duels; 912 draws): 40.4% [37.2–43.6]; unique-class gradient 65%→38%→29%→0% across 7/8/9/10 pieces.



**Budget honesty (AX-31 instantiated):** an initial 800 ms clock left 12 unproven; forensic re-test showed all resolved ≤1.7 s and the advertised 120k node cap could never fire behind the clock (dead code). Budgets raised to 2,500 ms / 400k; change recorded in the run, not silently applied.



**Screen doctrine (two negative results):** a cheap pre-screen is (a) a *bias amplifier* in mate-dense populations — truncation selects hardness, and hardness is where duels live (44 of 116 duels invisible at quarter budget, unweightable because unobserved); (b) merely *unaffordable* in inert populations — 1.23× cost, no crossover, because the full check's cost IS the work. The assistant's own decision rule contained a vacuous clause (screen-agreement can never fail when a completed screen IS the exhaustive search) — caught by Base44; decision rules for experiments require the same adversarial review as the experiments. **Doctrine:** full verification on every draw; any filter whose truncation correlates with the predicate is a bias amplifier.



**Material confound — falsified by intervention, not argument:** stripping heavy duels to 6–9 pieces and padding light duels to 24+ never flipped the key's class (one intermediate flip was a different duel, not a class change). The anatomy belongs to the net, not the board. Caveat kept: the heavy arm remains 3 hand-built puzzles plus l2-perturbations — pedigree, not independence.



**Anatomy finding (placement-sensitive proxy, small n):** under one mechanical definition (does the quiet key attack any black piece from its destination?), library-lineage keys are direct attacks 8/8; light-pool keys attack nothing 0/5 (two are KING MOVES — Kf7, Kf8). Candidate mechanism for the psychological stakes: square-control keys are invisible along exactly the salience dimensions attacks and checks occupy. Known defect: the classifier is placement-sensitive (a pawn on an already-covered square flipped a label); must be redefined on net geometry before any general claim. Pool-hunt corroboration: 4 new independent light duels in ~26k fresh draws (1/6,475), each proof-stored.



**Robustness trait proposed:** padding-survival as a measurable net property (light 5 refused ~50 additions — tuned-to-the-square; broad-basin nets are exactly what generation wants as seeds).



**Process findings:** a ported verifier was gated 13/13 against known duels before running (cross-stack equivalence, applied to a port); synthetic stripped/padded positions were barred from the research pool (provenance inbreeding); the 912-draw local-light run saved zero examples (verified-but-unlogged is ephemeral — replayable from seed+segments, and tag-at-verification is the structural fix); Base44 self-audited its own strata arithmetic to closure (156 = 13+107+36+0) and surfaced a second defect unprompted. A lowercase-piece-type classifier bug was caught by a suspiciously clean result — the complement of truncation-selects-hardness is cleanliness-selects-bugs.



**Open:** independent heavy lineages (breaking the l2 pedigree); net-geometry classifier spec + tag-at-verification; the stratified six-hour global run (full checks, chunked streams); the 63 horizon-edge mate-3-only positions as a named population.



*End of Addendum II.*
