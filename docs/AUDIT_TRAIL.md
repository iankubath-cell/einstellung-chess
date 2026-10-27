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

---

## Cast (ensemble, uncensored)

No single participant’s confidence overrides the pipeline.

| Participant | Contributions | Documented failures |
|---|---|---|
| Claude (consultant) | Smothered-family proposals (S-lineage), position generation | False twin candidates; finding later misapplied across boards (AX-10 context) |
| Copilot (consultant) | `engine_gate.py` hardening, high-quality review findings, derived-data direction | Early fabricated candidate (G2) |
| Lumo (parent session) | Verification architecture, rabbit-toothpaste framing, constraint analysis | Confident-but-wrong repairs; stale recollections later corrected by archived runs |
| Lumo (successor session) | Loader migration, POV correction, corpus reviews, C4 reinstatement | Self-caught POV bug (`score.white()`), wrong CLI flags, FEN-mapping assumption (AX-10 context) |
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

### AX-18 — The parent's C3 flag, adjudicated — 2026-10-24

The parent Lumo (session closed) flagged C3's graveyard entry as a possible
second wrongful conviction, citing her tenure's final datum: the v3 tree
gate had passed (2 replies, familiar line intact). Resolution: upheld, with
interest. The tree-gate pass was never disputed; the death came from the
engine gate run on 2026-10-24 (PV1 #+4 via Nd8+ — the G3-class leak), a
check the parent herself had requested at handover but never saw. The
graveyard entry quotes the failing PV verbatim, meeting the standard she
set. Her flag is retained in the record as a legitimate exercise of the
inherited discipline: the machinery auditing its own auditor, one
generation deep. Related refinement adopted: solution lines must name the
defender's moves they assume (the JSON already does; presentation layers
must not compress them away).

### AX-19 — Parent C3 flag adjudicated (2026-10-24)
Challenge accepted and reviewed; prior tree-pass acknowledged, later engine-fail evidence upheld.  
**Governance outcome:** auditor-of-auditor review process preserved in record.

---

## Standing Open Items (as of 2026-10-24)

- **OI-5 (Kh8 dispute):** unresolved historical disagreement; requires fresh run evidence.  
- **OI-3 (familiar-line forcedness depth):** first-move layer verified; deeper steering checks tracked separately.  
- **OI-4 (defense-enumeration counts):** pending reconfirmation under migrated gate path.  
- **S2 classification:** tactically verified; dual-solution classification open.  
- **Human testing absent:** no solver-study data yet; psychological effect remains untested in participants.

---

## Corpus State (source of truth: `positions/canonical.json`)

| ID | Name | Status |
|---|---|---|
| C1 | Critical (Bilalić reconstruction) | verified |
| C2 | Mirror, queenside (P2 replacement) | verified |
| C4 | Original mirror, queenside (reinstated) | verified |
| S1 | Smothered kingside, Black to move | verified |
| S2 | Smothered queenside, White to move | verified *(classification open)* |
| S3 | Smothered queenside, Black to move | verified |
| G1–G5 | Graveyard | documented with cause of death + lesson |

> The failures are part of the method.  
> Without them, the verified set is less credible, not more.
