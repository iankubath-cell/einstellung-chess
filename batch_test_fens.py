import sys
import chess

# ---------------------------------------------------------------
# Exhaustive forced-mate search (White to move). Fine for n <= 3.
# ---------------------------------------------------------------
def white_mates(b, n):
    if n < 1:
        return False
    for m in list(b.legal_moves):
        b.push(m)
        try:
            if b.is_checkmate():
                return True
            if n > 1 and not b.is_game_over():
                if all(_after(b, r, n - 1) for r in list(b.legal_moves)):
                    return True
        finally:
            b.pop()
    return False

def _after(b, reply, n):
    b.push(reply)
    try:
        return white_mates(b, n)
    finally:
        b.pop()

def shortest_mate(board, max_n=3):
    for n in range(1, max_n + 1):
        if white_mates(board.copy(), n):
            return n
    return None

# ---------------------------------------------------------------
# Replay with suffix verification
# ---------------------------------------------------------------
def replay(board, moves):
    """Returns (legal, checkmate, message)."""
    b = board.copy()
    for i, san in enumerate(moves, 1):
        try:
            mv = b.parse_san(san)
        except ValueError as e:
            return False, False, f"move {i} '{san}' illegal ({e})"
        actual = b.san(mv)
        if actual != san:
            return False, False, f"move {i}: wrote '{san}' but position gives '{actual}'"
        b.push(mv)
    return True, b.is_checkmate(), "checkmate" if b.is_checkmate() else "not checkmate"

# ---------------------------------------------------------------
# Position sets: lines are specific to each geometry
# ---------------------------------------------------------------
FAMILIAR_KS = ["Qe6+", "Kh8", "Nf7+", "Kg8", "Nh6+", "Kh8", "Qg8+", "Rxg8", "Nf7#"]
SHORT_KS = {
    "Rd7":  ["Qe6+", "Kh8", "Qh6", "Rd7", "Qxh7#"],
    "Rxd4": ["Qe6+", "Kh8", "Qh6", "Rxd4", "Qxh7#"],
    "Kg8":  ["Qe6+", "Kh8", "Qh6", "Kg8", "Qxg7#"],
    "Kf8 (Nxh7)": ["Qe6+", "Kf8", "Nxh7#"],
    "Kf8 (Qf7)":  ["Qe6+", "Kf8", "Qf7#"],
}

POSITIONS = [
    # label, fen, familiar line, {name: short line}
    ("Critical (2-sol)", "3r2k1/pp4pp/8/6N1/1b1B4/8/PP2QPPP/R4K1R w - - 0 1",
     FAMILIAR_KS, SHORT_KS),
    ("Extinction c6", "3r2k1/pp4pp/2b5/6N1/3B4/8/PP2QPPP/R4K1R w - - 0 1",
     FAMILIAR_KS, SHORT_KS),
    ("Extinction f6", "3r2k1/pp4pp/5b2/6N1/3B4/8/PP2QPPP/R4K1R w - - 0 1",
     FAMILIAR_KS, SHORT_KS),
    ("Extinction a4", "3r2k1/pp4pp/8/6N1/b2B4/8/PP2QPPP/R4K1R w - - 0 1",
     FAMILIAR_KS, SHORT_KS),
    ("Extinction f6+f8N", "3r1nk1/pp4pp/5b2/6N1/3B4/8/PP2QPPP/R4K1R w - - 0 1",
     FAMILIAR_KS, SHORT_KS),
    # Add the Claude mirror here with its own mirrored lines.
]

def run_tests(label, fen, familiar, short_lines):
    print("=" * 64)
    print(f"TESTING: {label}\nFEN: {fen}")
    print("-" * 64)
    try:
        board = chess.Board(fen)
    except ValueError as e:
        print(f"[X] INVALID FEN: {e}\n")
        return
    if not board.is_valid():
        print(f"[X] Illegal position: {board.status()!r}\n")
        return
    if board.turn != chess.WHITE:
        print("[X] Expected White to move\n")
        return

    legal, mate, msg = replay(board, familiar)
    familiar_ok = legal and mate
    print(f"Familiar line: {'OK' if familiar_ok else 'FAIL'} ({msg})")

    short_ok = {}
    for name, line in short_lines.items():
        legal, mate, msg = replay(board, line)
        short_ok[name] = legal and mate
        print(f"Short [{name}]: {'OK' if short_ok[name] else 'no'} ({msg})")
        if short_ok[name] and line[0] != familiar[0]:
            print("   [!] first move differs from familiar line")

    n = shortest_mate(board, max_n=3)
    print(f"Exhaustive search: shortest forced mate <= 3 -> "
          f"{n if n else 'none within 3'}")

    print("-" * 64)
    if familiar_ok and n is not None and n <= 3:
        print("STATUS: DUAL (familiar mate + shorter forced mate exist)")
    elif familiar_ok and n is None:
        print("STATUS: TWIN CANDIDATE (no forced mate in <= 3; confirm familiar "
              "line is forced with the engine gate)")
    else:
        print("STATUS: FAILED / PARTIAL")
    print()

def main():
    print(f"BATCH FEN TESTER - {len(POSITIONS)} positions\n")
    for label, fen, fam, shorts in POSITIONS:
        run_tests(label, fen, fam, shorts)

if __name__ == "__main__":
    sys.exit(main())