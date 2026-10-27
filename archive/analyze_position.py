import os
import sys
import chess
import chess.engine


def main():
    fen = "r1bq1rk1/pp3ppp/8/3pn3/1b6/1N1B4/PP3PPP/R1BQ1K1R w - - 0 1"

    # --- Board setup ---
    try:
        board = chess.Board(fen)
    except ValueError as e:
        print(f"Invalid FEN: {e}")
        sys.exit(1)

    print("Position legal:", board.is_valid())
    print("FEN:", board.fen())
    print()

    # --- Engine setup ---
    engine_path = os.environ.get("STOCKFISH_PATH")
    if not engine_path:
        print("Error: STOCKFISH_PATH is not set.")
        sys.exit(2)
    if not os.path.isfile(engine_path):
        print(f"Error: STOCKFISH_PATH does not point to a file: {engine_path}")
        sys.exit(2)

    try:
        with chess.engine.SimpleEngine.popen_uci(engine_path) as eng:
            # Top 3 moves
            infos = eng.analyse(board, chess.engine.Limit(depth=20), multipv=3)
            if not isinstance(infos, list):
                infos = [infos]

            print("Top moves for White (depth 20):")
            for i, info in enumerate(infos, start=1):
                pv = info.get("pv", [])
                score = info.get("score")
                if not pv or score is None:
                    print(f"  PV{i}: incomplete engine info")
                    continue
                move = pv[0]
                san = board.san(move)
                eval_white = score.white()
                print(f"  PV{i}: {san:8} eval: {eval_white}")

            # Evaluate specific move Qh5
            print()
            move_san = "Qh5"
            test_board = board.copy()
            try:
                move = test_board.parse_san(move_san)
            except ValueError as e:
                print(f"{move_san} is illegal in this position: {e}")
                return

            test_board.push(move)
            info = eng.analyse(test_board, chess.engine.Limit(depth=20))
            score = info.get("score")
            if score is None:
                print(f"After {move_san}, engine returned no score.")
            else:
                print(f"After White plays {move_san}, eval from White's view: {score.white()}")
                print("(positive = good for White)")
    except chess.engine.EngineError as e:
        print(f"Engine error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()