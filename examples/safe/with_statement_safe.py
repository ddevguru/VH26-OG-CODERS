def read_safe(path):
    with open(path, "r") as f:
        return f.read()
