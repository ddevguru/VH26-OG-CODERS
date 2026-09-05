import gc

leaked_objects = []

class Data:
    def __init__(self):
        self.data = "X" * 1_000_000  # ~1 MB

def create_leak():
    obj = Data()
    leaked_objects.append(obj)  # reference permanently stored

for i in range(100):
    create_leak()

print("Objects stored:", len(leaked_objects))
print("Approx memory retained:", len(leaked_objects), "MB")

gc.collect()