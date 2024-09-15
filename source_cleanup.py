import sys

def main():
    source_path = sys.argv[1]
    with open(source_path) as f:
        source = f.read()

    source = source.replace("’", "'").replace("”", "\"").replace("“", "\"").replace("…", "...").replace("—", "-")

    with open(source_path, "w") as f:
        f.write(source)

if __name__ == "__main__":
    main()