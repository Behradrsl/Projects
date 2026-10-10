"""Play Tic Tac Toe with someone at the same keyboard."""

import argparse

from tic_tac_toe import TicTacToe


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="A two-player terminal Tic Tac Toe game."
    )
    parser.add_argument(
        "--first", choices=["X", "O"], help="Choose who starts each round."
    )
    args = parser.parse_args(argv)
    print("Tic Tac Toe\nTwo players: X and O. Choose a cell from 1 to 9, or q to quit.")
    try:
        while True:
            game = TicTacToe(args.first)
            print(f"\nPlayer {game.current_player} starts.")
            while not game.finished:
                print(f"\n{game}\n")
                choice = input(f"Player {game.current_player}, your move: ").strip()
                if choice.lower() == "q":
                    return 0
                try:
                    game.play(int(choice))
                except ValueError as error:
                    print(
                        str(error)
                        if choice.isdigit()
                        else "Enter a number from 1 to 9, or q to quit."
                    )
            print(f"\n{game}\n")
            print(f"Player {game.winner} wins!" if game.winner else "It's a draw!")
            if input("Play again? [y/N]: ").strip().lower() != "y":
                return 0
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
