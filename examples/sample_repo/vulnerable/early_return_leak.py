def process_early_return(flag: bool, path: str):
    f = open(path, "r")
    if flag:
        return None  # LEAK: f is unclosed on early return branch
    data = f.read()
    f.close()
    return data


def unclosed_resource_leak(path: str):
    f = open(path, "r")
    return f.read()  # DEFINITE_LEAK: f is acquired but never closed
