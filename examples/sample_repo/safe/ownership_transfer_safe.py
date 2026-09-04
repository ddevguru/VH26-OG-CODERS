def create_stream(path: str):
    f = open(path, "w")
    return f  # SAFE: ownership transferred to caller via return statement
