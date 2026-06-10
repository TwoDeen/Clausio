import argparse
import random
import sys


def get_random_line(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if not lines:
            print(f"Error: '{filename}' is empty.", file=sys.stderr)
            return

        # Pick and print a random line (stripping trailing newlines)
        print(random.choice(lines).rstrip("\r\n"))

    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Pick a random line from a text file."
    )
    parser.add_argument(
        "filename", type=str, help="The path to the text file."
    )

    args = parser.parse_args()
    get_random_line(args.filename)
