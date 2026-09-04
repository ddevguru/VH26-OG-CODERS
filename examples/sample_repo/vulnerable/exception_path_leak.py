def parse_content(data: str):
    if not data:
        raise ValueError("Empty data format")
    return len(data)


def process_exception_path(path: str):
    f = open(path, "r")
    data = f.read()
    parse_content(data)  # Call that may raise exception bypassing f.close()
    f.close()
    return data
