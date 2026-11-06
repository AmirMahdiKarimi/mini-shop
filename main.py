"""Entry point for the graphical and text interfaces."""

import argparse
import sys

from shop import cli, gui
from shop.config import DATABASE_PATH
from shop.service import ShopService
from shop.storage import SQLiteStore


def main() -> None:
    # Windows shells can default to cp1252, which cannot print Persian CLI text.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="مدیریت فروشگاه کوچک")
    parser.add_argument("--cli", action="store_true", help="اجرای رابط متنی")
    args = parser.parse_args()

    service = ShopService(store=SQLiteStore(path=DATABASE_PATH))
    if args.cli:
        cli.run(service=service)
    else:
        gui.run(service=service)


if __name__ == "__main__":
    main()
