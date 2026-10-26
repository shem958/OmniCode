import os
import sys

lock_path = os.path.join(os.path.dirname(__file__), "..", "qdrant_storage", ".lock")
print(f"Checking lock file at: {lock_path}")

if os.path.exists(lock_path):
    try:
        os.remove(lock_path)
        print("Success: Stale Qdrant .lock file successfully removed!")
    except Exception as e:
        print("Error: Could not remove lock file. A process is actively holding the lock:", str(e))
        sys.exit(1)
else:
    print("No lock file found.")
