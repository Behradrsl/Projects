"""Play Monty Hall, or compare strategies with repeated simulations."""

import argparse

from monty_hall import create_round, simulate_games


def ask_number(prompt: str, minimum: int, maximum: int, default: int | None = None) -> int:
    while True:
        answer = input(prompt).strip()
        if not answer and default is not None:
            return default
        try:
            number = int(answer)
            if minimum <= number <= maximum:
                return number
        except ValueError:
            pass
        print(f"Please enter a whole number from {minimum:,} to {maximum:,}.")


def play() -> None:
    print("\nOne car, two goats. Which door will you choose?")
    choice = ask_number("Choose door 1, 2, or 3: ", 1, 3)
    game = create_round(choice)
    print(f"Monty opens door {game.revealed}. It has a goat.")
    while True:
        action = input(f"Keep door {choice} (k), or switch to door {game.remaining} (s)? ").lower()
        action = action.strip()
        if action in ("k", "keep", "s", "switch"):
            break
        print("Enter k to keep your door, or s to switch.")
    switch = action in ("s", "switch")
    print(f"The car was behind door {game.car}.")
    print("You won the car!" if game.won(switch) else "You got a goat. Try another round!")


def show_simulation(games: int, seed: int | None = None) -> None:
    stay, switch = simulate_games(games, seed)
    print(f"\nResults for {games:,} games")
    if seed is not None:
        print(f"Random seed: {seed}")
    print(f"Keep your door: {stay:,} wins ({stay / games:.2%})")
    print(f"Switch doors:   {switch:,} wins ({switch / games:.2%})")
    print("\nExpected over many games: keep ≈ 1/3, switch ≈ 2/3.")
    print("Both strategies are compared on the same games. Small samples can vary.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Play or simulate the Monty Hall problem.")
    parser.add_argument("--games", type=int, help="Run 1–1,000,000 games instead of the menu")
    parser.add_argument("--seed", type=int, help="Repeat a simulation with the same random seed")
    args = parser.parse_args(argv)
    if args.games is not None:
        try:
            show_simulation(args.games, args.seed)
        except ValueError as exc:
            parser.error(str(exc))
        return 0
    if args.seed is not None:
        parser.error("Use --seed together with --games.")

    print("\nMonty Hall")
    print("Monty always opens an unchosen goat door, then offers you a switch.")
    try:
        while True:
            print("\n1. Play a round\n2. Compare strategies\n0. Exit")
            choice = input("Your choice: ").strip()
            if choice in ("0", "q"):
                break
            if choice == "1":
                play()
            elif choice == "2":
                games = ask_number("How many games? [10000]: ", 1, 1_000_000, 10000)
                show_simulation(games)
            else:
                print("Please choose 1, 2, or 0.")
    except (KeyboardInterrupt, EOFError):
        print()
    print("Goodbye!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
