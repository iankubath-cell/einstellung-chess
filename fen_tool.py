import chess

fen = input("Paste FEN: ").strip()

try:
    board = chess.Board(fen)
except ValueError as e:
    print("INVALID FEN:", e)
    raise SystemExit

print()
print(board)
print()
print("Legal position :", board.is_valid())
print("Side to move   :", "White" if board.turn else "Black")
print("Castling rights:", board.castling_xfen())
print("Normalised FEN :", board.fen())