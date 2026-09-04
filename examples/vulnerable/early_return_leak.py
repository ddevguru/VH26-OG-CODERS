def process_user(user_id):
    f = open("data.txt", "w")

    if user_id is None:
        # Dangerous: Early return leaves file open!
        return

    f.close()
