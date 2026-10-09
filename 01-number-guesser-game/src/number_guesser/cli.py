"""Terminal interaction and application orchestration."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .game import DIFFICULTIES, Difficulty, Game, Status
from .storage import Record, ScoreStore, StorageError

RULES = """Guess the secret number before your attempts run out.
Each wrong guess gives a higher/lower hint and reduces your score.
Invalid input and repeated guesses do not consume attempts.

During a round:
  help       Show these commands
  history    Show your guesses
  quit       End the round and exit

A win starts at 100 points, minus the difficulty's penalty per wrong guess.
An exhausted or abandoned round scores 0. Rankings are separate per difficulty.
"""


def player_name(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 24 or any(not c.isprintable() for c in value):
        raise argparse.ArgumentTypeError("Name must be 1–24 printable characters.")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="number-guesser",
        description="A terminal guessing game with saved scores and three difficulty levels.",
    )
    result.add_argument("--difficulty", choices=DIFFICULTIES, help="Skip the difficulty menu")
    result.add_argument("--name", type=player_name, help="Player name (1–24 characters)")
    result.add_argument("--stats", action="store_true", help="Show saved statistics and exit")
    result.add_argument("--no-save", action="store_true", help="Play without saving rounds")
    result.add_argument(
        "--scores-file",
        type=Path,
        default=Path.home() / ".number_guesser" / "scores.json",
        help="History file (default: ~/.number_guesser/scores.json)",
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return result


def show_stats(store: ScoreStore, name: str | None = None) -> bool:
    try:
        rounds = store.load()
    except StorageError as exc:
        print(f"\nWarning: {exc}", file=sys.stderr)
        return False
    if name is not None:
        rounds = [record for record in rounds if record.player == name]
    print(f"\nSTATISTICS{' · ' + name if name else ''}")
    if not rounds:
        print("No saved rounds yet. Play a round to start your history.")
        return True
    wins = sum(record.outcome == "won" for record in rounds)
    losses = sum(record.outcome == "lost" for record in rounds)
    print(
        f"Rounds: {len(rounds)}  |  Wins: {wins}  |  Losses: {losses}  |  "
        f"Quit: {len(rounds) - wins - losses}"
    )
    print(f"Win rate: {wins / len(rounds):.0%}")
    for difficulty in DIFFICULTIES:
        winners = sorted(
            (r for r in rounds if r.difficulty == difficulty and r.outcome == "won"),
            key=lambda r: (-r.score, r.attempts, r.played_at),
        )[:5]
        if not winners:
            continue
        print(f"\n{difficulty.upper()} · TOP 5 WINNING ROUNDS")
        print(f"{'#':<3} {'Player':<24} {'Score':>5} {'Guesses':>8}  Date (UTC)")
        for position, record in enumerate(winners, 1):
            print(
                f"{position:<3} {record.player:<24} {record.score:>5} "
                f"{record.attempts:>8}  {record.played_at[:10]}"
            )
    return True


def choose_difficulty(store: ScoreStore) -> Difficulty | None:
    print("\nDifficulty     Range       Attempts   Wrong-guess penalty")
    for index, mode in enumerate(DIFFICULTIES.values(), 1):
        print(
            f"{index}. {mode.name.title():<9} 1–{mode.upper:<8} "
            f"{mode.attempts:<10} {mode.penalty} points"
        )
    print("\nType stats for your leaderboard, or quit to exit.")
    shortcuts = dict(zip(("1", "2", "3"), DIFFICULTIES, strict=False))
    while True:
        choice = input("Difficulty [normal]: ").strip().lower() or "normal"
        choice = shortcuts.get(choice, choice)
        if choice in DIFFICULTIES:
            return DIFFICULTIES[choice]
        if choice in ("quit", "q"):
            return None
        if choice == "stats":
            show_stats(store)
        else:
            print("Choose easy, normal, hard, stats, or quit.")


def play_round(game: Game, name: str) -> int | None:
    """Return an exit code if the user exits, otherwise allow another round."""
    mode = game.difficulty
    print(f"\n{name}, a number between 1 and {mode.upper} is waiting.")
    print(f"{mode.name.title()} · {mode.attempts} attempts · {mode.penalty} points per wrong guess")
    print("Type help for commands.\n")
    while game.status == Status.PLAYING:
        print(
            f"Possible range: {game.lower_bound}–{game.upper_bound}  |  "
            f"Attempts left: {game.attempts_left}  |  Score: {game.score}"
        )
        try:
            raw = input("Your guess > ").strip().lower()
        except (EOFError, KeyboardInterrupt) as exc:
            game.quit()
            print("\nRound ended. Goodbye!")
            return 130 if isinstance(exc, KeyboardInterrupt) else 0
        if raw in ("quit", "q", "exit"):
            game.quit()
            print(f"Round ended. The number was {game.answer}. Score: 0. Goodbye!")
            return 0
        if raw in ("help", "?"):
            print(RULES)
            continue
        if raw == "history":
            print("Your guesses: " + (", ".join(map(str, game.guesses)) or "none yet"))
            continue
        try:
            result = game.guess(int(raw))
        except ValueError as exc:
            if not raw.lstrip("+-").isdigit():
                print("Enter a whole number, or type help for commands.")
            else:
                print(exc)
            continue
        if result.status == Status.WON:
            count = len(game.guesses)
            print(f"\nCorrect! The number was {game.answer}.")
            print(
                f"You won in {count} {'guess' if count == 1 else 'guesses'} · "
                f"Final score: {game.score}/100"
            )
        elif result.status == Status.LOST:
            print(f"\nOut of attempts. The number was {game.answer}. Final score: 0/100")
        else:
            print(f"Go {result.direction}!\n")
    return None


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = ScoreStore(args.scores_file.expanduser())
    if args.stats:
        return 0 if show_stats(store, args.name) else 1
    print("\n" + "=" * 54)
    print("  NUMBER GUESSER  ·  Think. Guess. Narrow it down.")
    print("=" * 54)
    if args.no_save:
        print("Practice mode: rounds will not be saved.")
    try:
        name = args.name
        while name is None:
            try:
                name = player_name(input("Player name [Player]: ").strip() or "Player")
            except argparse.ArgumentTypeError as exc:
                print(exc)
        mode = DIFFICULTIES[args.difficulty] if args.difficulty else choose_difficulty(store)
        while mode is not None:
            game = Game(mode)
            exit_code = play_round(game, name)
            if not args.no_save:
                try:
                    store.append(Record.from_game(name, game))
                except StorageError as exc:
                    print(f"Warning: {exc}\nThis round was not saved.", file=sys.stderr)
            if exit_code is not None:
                return exit_code
            while True:
                choice = input("\nPlay again? [y]es / [m]ode / [s]tats / [n]o: ").strip().lower()
                if choice in ("y", "yes", ""):
                    break
                if choice in ("m", "mode"):
                    mode = choose_difficulty(store)
                    break
                if choice in ("n", "no", "q", "quit"):
                    print("Thanks for playing!")
                    return 0
                if choice in ("s", "stats"):
                    show_stats(store, name)
                else:
                    print("Choose yes, mode, stats, or no.")
        print("Goodbye!")
        return 0
    except EOFError:
        print("\nGoodbye!")
        return 0
    except KeyboardInterrupt:
        print("\nGoodbye!")
        return 130
