\# Base44 "Length Duel" specimens -- verified 2026-11-16

Root-divergent strong form: quiet root move mates in 2, loud check mates in 3+.

Verified by THREE independent exhaustive enumerators: chess.js (Base44),

fen\_eval.py exact probe, oracle.Solver (len\_after, certification-grade).

Archive tier: fails only `shared\_first\_move\_broken` under the current contract.



\## 1. "The Rook, Not the Queen"

FEN: 1nb3qk/pp3ppp/3R3N/8/7Q/1B5P/5PPP/6K1 w - - 0 1

QUIET key Rd8 = mate in 2 (oracle.Solver: exact total 2, 20 nodes).

Loud Nxf7+ = mate in 3 (EXACT). 31 slower preserving roots incl. quiet Qd8 (3).



\## 2. "One Check, One Quiet Queen"  \[richest specimen]

FEN: 1n6/kp2N3/p2Q4/2N4K/8/8/8/8 w - - 0 1

QUIET key Qc7 = mate in 2 (oracle.Solver: exact total 2, 4 nodes).

Loud Nc8+ = mate in 3 (EXACT). NEW TEXTURE: three checking roots mate NOWHERE

(Qxb8+, Qb6+, Qxa6+) -- "loud and empty."



\## 3. "Five Quiet Steps, One Loud Check"  \[TWIN-CANDIDATE, Option B ore]

FEN: k6n/pn2R3/3QR3/8/8/2K5/8/8 w - - 0 1

FIVE quiet mate-in-2 roots: Qd7, Qc7, Qc6, Qa6, Qd5 (Qd7: exact total 2, 9 nodes).

Loud Re8+ = mate in 3 (EXACT). Richest twins-ore find to date (5-fold tie).



Scarcity context: Base44's own recorded search -- 673 candidates across 4 seeded

batches -- produced ZERO new hits; these three are hand/productive search finds.

Quiet Offer caption (gxh6 refutation claim) was FALSIFIED by fen\_eval (Rc8 mates

in 3 exactly) -- captions lose to machines, as tradition demands.

