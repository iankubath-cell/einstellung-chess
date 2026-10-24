import os
import chess
import chess.engine

engine_path = os.environ.get("STOCKFISH_PATH")
print("engine path:", engine_path)

board = chess.Board()
print("board loaded:", board.fen())

eng = chess.engine.SimpleEngine.popen_uci(engine_path)
info = eng.analyse(board, chess.engine.Limit(depth=10))
eng.quit()

print("score:", info["score"].white())
print("TRANSPORT TEST PASSED")