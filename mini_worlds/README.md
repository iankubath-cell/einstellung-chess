# Mini-worlds duel census

Reproduce: gcc -O2 -DMAXSQ=64 -o census census.c ; ./census N K        (exact; white-king orbit reps x orbit size = raw counts)
           gcc -O2 -DMAXSQ=64 -o census2 census2.c ; ./census2 N0 K N1  (embed every N0 duel into an empty N1 board at all offsets)
           gcc -O2 -DMAXSQ=64 -o census3d census3d.c ; ./census3d N K SAMPLES SEED [dump]   (uniform random sampler; "dump" writes FEN+category to stderr)
           python3 census_py.py N K [workers]   (independent re-implementation, full raw enumeration)
           python3 xcheck.py   (needs python-chess, dump_k*.txt, and the project's oracle.py copied to orc/his_oracle.py)

Position class: N x N board, white king, black king, K non-king pieces each Q/R/B/N of either colour (8 labels, uniform), no pawns,
no castling / en passant, WHITE to move, black king not in check, white king not in check (excluded, a simplification), kings not adjacent.

Duel predicate (MY READING of "strict predicate"; check it against the project's definition):
  no root move mates in 1;
  no LOUD root (gives check or captures) forces mate within 2;
  at least one QUIET root (neither) forces mate in exactly 2;
  at least one CHECKING root forces mate in exactly 3.
"Forces mate in n" = the bundled exhaustive search with the defender trying every legal reply; stalemate is not a win.
Categories printed: legal, mate_in_1_exists, loud_mate_in_2, no_mate_in_2_at_all, quiet_m2_but_no_check_m3, DUELS, degenerate (white has no legal move), any_mate_in_2.
