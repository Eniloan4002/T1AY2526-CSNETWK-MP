import argparse
from networking.logger import MessageLogger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logger = MessageLogger(args.verbose)

    if args.verbose:
        print("[VERBOSE MODE ENABLED]")

    while True:
        print("==============================")
        print("       7 WONDERS GAME")
        print("==============================")
        print()
        print("1. Create Game")
        print("2. Join Game")
        print("3. Exit")
        print()

        choice = input("Enter your choice: ")

        if choice == "1":
            print("\nCreate Game selected!")
        elif choice == "2":
            print("\nJoin Game selected!")
        elif choice == "3":
            print("\nThank you for playing!")
            break
        else:
            print("\nInvalid choice. Please try again.")

        print()


if __name__ == "__main__":
    main()