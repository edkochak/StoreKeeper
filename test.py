import os, sys, tokenize, io


def remove_comments(src_bytes):
    tokens = tokenize.tokenize(io.BytesIO(src_bytes).readline)
    filtered = []
    for toknum, tokval, *_ in tokens:
        if toknum == tokenize.COMMENT:
            continue
        filtered.append((toknum, tokval))
    return tokenize.untokenize(filtered)


def process_file(path):
    with open(path, "rb") as f:
        src = f.read()
    new_src = remove_comments(src)
    with open(path, "wb") as f:
        f.write(new_src)
    print(f"Stripped comments: {path }")


def main(root):
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn.endswith(".py"):
                process_file(os.path.join(dirpath, fn))


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root)
