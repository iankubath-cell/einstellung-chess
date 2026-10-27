"""S2 exactness adjudication — three restricted-root-move queries.

Settles whether 3.Nxe8+ beats the smothered finish after 1.Qd6+ Ka8 2.Nc7+ Kb8.
Per Claude's S2 exactness test: A1 -> #3, B1 -> #2, B2 -> #3 if the claim holds.
"""
import chess
import chess.engine as e

ENGINE = r"C:\Users\44777\Downloads\stockfish-windows-x86-64-universal\stockfish\stockfish-windows-x86-64-universal.exe"

QUERIES = [
    ("A1", "After 1.Qd6+ Ka8, is Nc7+ mate in 3?",
     "k3r3/pp3ppp/3Q1nnp/1N5b/4B3/P6P/PPP3P1/R1K4R w - - 2 2", "Nc7+"),
    ("B1", "After 2.Nc7+ Kb8, is Nxe8+ mate in 2?",
     "1k2r3/ppN2ppp/3Q1nnp/7b/4B3/P6P/PPP3P1/R1K4R w - - 4 3", "Nxe8+"),
    ("B2", "After 2.Nc7+ Kb8, is Na6+ mate in 3?",
     "1k2r3/ppN2ppp/3Q1nnp/7b/4B3/P6P/PPP3P1/R1K4R w - - 4 3", "Na6+"),
]

EXPECTED_IF_RIGHT = {"A1": "#3", "B1": "#2", "B2": "#3"}

def main():
    s = e.SimpleEngine.popen_uci(ENGINE)
    print("S2 EXACTNESS ADJUDICATION")
    print("-" * 70)
    for qid, desc, fen, san in QUERIES:
        board = chess.Board(fen)
        move = board.parse_san(san)
        info = s.analyse(board, e.Limit(depth=28), root_moves=[move])
        score = info["score"].pov(board.turn)
        pv = board.variation_san(info["pv"]) if "pv" in info else "(no pv)"
        got = f"#{score.mate()}" if score.is_mate() else str(score)
        verdict = "CLAIM SUPPORTED" if got == EXPECTED_IF_RIGHT[qid] else "CLAIM REFUTED"
        print(f"{qid}: {desc}")
        print(f"    FEN: {fen}")
        print(f"    restricted to {san}: {got}   (expected if claim right: {EXPECTED_IF_RIGHT[qid]})")
        print(f"    PV: {pv}")
        print(f"    >>> {verdict}")
        print()
    s.quit()

if __name__ == "__main__":
    main()