"""Issue a seven-day, handle-bound research desk pass on the Goldbach host."""

import argparse
import os
import time
from pathlib import Path

from desk import canonical_handle, fleet_pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handle")
    parser.add_argument("output", type=Path, help="new private file for the fleet controller")
    parser.add_argument("--secret-file", type=Path, default=Path("/etc/goldbach-web/webhook"))
    args = parser.parse_args()
    handle = canonical_handle(args.handle)
    if not handle:
        parser.error("invalid GitHub login")
    expires = int(time.time()) + 7 * 86400
    ticket = fleet_pass(args.secret_file.read_bytes().strip(), handle, expires)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as stream:
        stream.write(ticket + "\n")
    print(f"Fleet pass saved for {handle}. Expires at Unix time {expires}.")


if __name__ == "__main__":
    main()
