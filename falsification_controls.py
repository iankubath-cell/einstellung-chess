import os
import sys
import chess
import chess.engine

MOVE_UCI = "h4h7"   # the Qxh7 test move, in UCI to avoid SAN ambiguity

# (label, FEN, expect_mate)
CONTROLS = [
    ("Base FEN",
     "3r1rk1/p4ppp/3p4/4P3/7Q/3B1N2/PP3PPP/4R1K1 w - - 0 1", True),
    # Bishop gone: h7 is no longer protected, so Kxh7 is possible.
    ("Remove bishop d3",
     "3r1rk1/p4ppp/3p4/4P3/7Q/5N2/PP3PPP/4R1K1 w - - 0 1", False),
    # Rook f8 -> e8: f8 is free, so the king can escape to f8.
    ("Move f8-rook to e8",
     "3rr1k1/p4ppp/3p4/4P3/7Q/3B1N2/PP3PPP/4R1K1 w - - 0 1", False),
    # Black knight on f6 can capture on h7.
    ("Add black knight f6",
     "3r1rk1/p4ppp/3p1n2/4P3/7Q/3B1N2/PP3PPP/4R1K1 w - - 0 1", False),
    # Black pawn on h6 blocks the h-file, so Qxh7 should be illegal.
    ("Pawn h6 blocks h-file",
     "3r1rk1/p4ppp/3p3p/4P3/7Q/3B1N2/PP3PPP/4R1K1 w - - 0 1", False),
]


def run_control(eng, label, fen, expect_mate, depth=14):
    """Returns (passed, detail)."""
    try:
        board = chess.Board(fen)
    except ValueError as e:
        return False, f"BAD FEN: {e}"
    if not board.is_valid():
        return False, f"INVALID POSITION: {board.status()!r}"

    move = chess.Move.from_uci(MOVE_UCI)
    if move not in board.legal_moves:
        # An illegal move can never be mate, so that satisfies expect_mate=False.
        return (not expect_mate), "Qxh7 illegal"

    after = board.copy()
    after.push(move)
    is_mate = after.is_checkmate()

    # Restrict the engine to Qxh7 so it can't report a different mate.
    info = eng.analyse(board, chess.engine.Limit(depth=depth), root_moves=[move])
    score = info["score"].white()
    sf_mate = score.mate() if score.is_mate() else None
    sf_says_mate_in_1 = (sf_mate == 1)

    if is_mate != sf_says_mate_in_1:
        return False, (f"DISAGREEMENT: python-chess mate={is_mate}, "
                       f"engine={score}")

    passed = (is_mate == expect_mate)
    return passed, f"Qxh7# = {is_mate}, engine = {score}"


def main():
    path = os.environ.get("STOCKFISH_PATH")
    if not path or not os.path.isfile(path):
        sys.exit("Set STOCKFISH_PATH to a valid Stockfish binary.")

    failures = 0
    print("FALSIFICATION CONTROLS")
    print("-" * 70)
    with chess.engine.SimpleEngine.popen_uci(path) as eng:
        for label, fen, expect in CONTROLS:
            try:
                ok, detail = run_control(eng, label, fen, expect)
            except Exception as e:   # one bad control shouldn't kill the run
                ok, detail = False, f"ERROR: {type(e).__name__}: {e}"
            failures += (not ok)
            print(f"{'PASS' if ok else 'FAIL':5} {label:26} "
                  f"expect_mate={expect!s:5} | {detail}")

    print("-" * 70)
    print("All controls behaved as expected." if not failures
          else f"{failures} control(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()