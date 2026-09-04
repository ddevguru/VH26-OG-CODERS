def process_with_statement(path: str) -> str:
    with open(path, "r") as f:
        return f.read()  # SAFE: managed by with context manager
