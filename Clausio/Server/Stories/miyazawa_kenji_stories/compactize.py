import sys

filename = sys.argv[1]

with open(filename, "r", encoding="utf-8") as f:
    lines = f.readlines()

with open(filename, "w", encoding="utf-8") as f:
    for line in lines:
        if line.strip():  # Skip empty/whitespace-only lines
            f.write(line)
