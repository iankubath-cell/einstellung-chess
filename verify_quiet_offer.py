#!/usr/bin/env python3
r"""verify_quiet_offer.py -- EXACT check (no engine) of Base44's claim:
after Qc8, EVERY Black reply allows White mate in one.
Pure enumeration; terminates in seconds; verdict is a proof, not a hint."""
import chess

B = chess.Board("5q1k/5ppp/2R4N/5Q2/8/8/5PPP/6K1 w - - 0 1")
key = None
for mv in B.legal_moves:
    if B.san(mv) == "Qc8":
        key = mv
        break
if key is None:
    raise SystemExit("Qc8 is not even legal -- FEN or claim is wrong")
B.push(key)

replies = list(B.legal_moves)
print(f"Qc8 legal; Black has {len(replies)} replies "
      f"(Base44 claimed nine)")
mates_for, escapes = {}, []
for rep in replies:
    rep_san = B.san(rep)
    B.push(rep)
    found = []
    for m in list(B.legal_moves):
        san = B.san(m)
        B.push(m)
        if B.is_checkmate():
            found.append(san)
        B.pop()
    if found:
        mates_for[rep_san] = found[0]
    else:
        escapes.append(rep_san)
    B.pop()

for r in sorted(mates_for):
    print(f"  {r:6} -> {mates_for[r]}#")
for r in sorted(escapes):
    print(f"  {r:6} -> ESCAPE (no mate-in-1 for White)")
if escapes:
    raise SystemExit(f"CLAIM REFUTED: {len(escapes)} escaping reply/ies")
print("VERIFIED: Qc8 is a forced mate in 2, exhaustively.")