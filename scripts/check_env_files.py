"""Reject tracked dotenv files without reading or printing their contents."""

import subprocess
import sys
from pathlib import PurePosixPath


def main() -> int:
    paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    forbidden = [
        path for path in paths
        if (name := PurePosixPath(path).name) != ".env.example"
        and (name == ".env" or name.startswith(".env."))
    ]
    if forbidden:
        print("Environment files must not be tracked; only .env.example is allowed:")
        for path in forbidden:
            print(f"  {path}")
        return 1
    print("Environment-file check passed (file names only; no contents read).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
