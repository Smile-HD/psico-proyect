"""Entry point: python -m app.seed [--reset]"""

from __future__ import annotations

import argparse
import sys

from app.db.session import SessionLocal
from app.seed.loader import reset_seed, run_seed


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.seed")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete seed-owned rows (reverse FK order), then re-seed",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            manifest = reset_seed(db)
            print(f"seed --reset ok (seed_version={manifest['seed_version']})")
        else:
            manifest = run_seed(db)
            print(f"seed ok (seed_version={manifest['seed_version']})")
        print("checksum:", manifest["checksum"])
        print("counts:", manifest["counts"])
        return 0
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
