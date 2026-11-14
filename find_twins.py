import chess

def any_mate_in_1(b):
    for mv in list(b.legal_moves):
        b.push(mv); m = b.is_checkmate(); b.pop()
        if m: return True
    return False

def mating_roots(fen):
    b = chess.Board(fen); roots = []
    for mv in list(b.legal_moves):
        san = b.san(mv); b.push(mv)
        if b.is_checkmate():
            roots.append((san, 1))
        elif not b.is_game_over():
            covered = True
            for reply in list(b.legal_moves):
                b.push(reply)
                if not any_mate_in_1(b): covered = False
                b.pop()
                if not covered: break
            if covered: roots.append((san, 2))
        b.pop()
    return roots

FENS = {
 "Tangled Rook":      "3r2k1/1p3ppp/8/1Q5r/8/8/8/4R1K1 w - - 0 1",
 "f7 Key (original)":  "rn4k1/5ppp/8/5NN1/1r6/1Q6/8/6K1 w - - 0 1",
 "f7 Key (my bad fix)":"rn4k1/5ppp/8/5NN1/1r6/8/1Q6/6K1 w - - 0 1",
 "Distant Attacker":   "3r2k1/5ppp/p7/8/Q6r/8/8/4R1K1 w - - 0 1",
 "Knight's Screen":    "rn4k1/5ppp/2p5/5NN1/1rQ5/8/8/6K1 w - - 0 1",
}
for name, fen in FENS.items():
    print(f"{name:20}", mating_roots(fen))