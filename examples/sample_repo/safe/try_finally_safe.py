def process_try_finally(path: str) -> str:
    f = open(path, "r")
    try:
        data = f.read()
        return data
    finally:
        f.close()  # SAFE: clean cleanup inside finally block
