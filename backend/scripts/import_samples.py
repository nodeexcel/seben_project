#!/usr/bin/env python3
"""Import all client sample files into the database."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.import_service import import_directory


def main():
    samples_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "samples")
    if len(sys.argv) > 1:
        samples_dir = sys.argv[1]

    print(f"Importing from: {samples_dir}")
    db = SessionLocal()
    try:
        stats = import_directory(db, samples_dir)
        print(f"Processed: {stats['processed']}, Failed: {stats['failed']}")
        for f in stats["files"]:
            print(f"  {f['file']}: {f['status']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
