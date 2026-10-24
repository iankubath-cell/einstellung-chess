import chess

# Critical problem (2-solution) FEN from Bilalić et al. (2008) Figure 1a
fen = "3r2k1/pp4pp/8/6N1/1b1B4/8/PP2QPPP/R4K1R w - - 0 1"
board = chess.Board(fen)
print("Position legal:", board.is_valid())
print("White to move:", board.turn == chess.WHITE)

fam_moves = ["Qe6+", "Kh8", "Nf7+", "Kg8", "Nh6+",
             "Kh8", "Qg8+", "Rxg8", "Nf7#"]
test_board = board.copy()
try:
    for san in fam_moves:
        test_board.push(test_board.parse_san(san))
    print("Familiar line legal:", test_board.is_checkmate())
    print("Familiar line moves played successfully")
except Exception as e:
    print("Familiar line error:", e)

alt_moves = ["Qe6+", "Kh8", "Qh6", "Rd7", "Qxh7#"]
test_board2 = board.copy()
try:
    for san in alt_moves:
        test_board2.push(test_board2.parse_san(san))
    print("Alternative line legal:", test_board2.is_checkmate())
    print("Alternative line moves played successfully")
except Exception as e:
    print("Alternative line error:", e)
