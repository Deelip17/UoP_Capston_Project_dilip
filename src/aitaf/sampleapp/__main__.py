import argparse
import sys
import time

from aitaf.sampleapp.mutations import CATALOGUE
from aitaf.sampleapp.server import DEMO_PASSWORD, DEMO_USER, ShopServer
from aitaf.sampleapp.snapshots import write_snapshots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitaf.sampleapp")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="start the sample shop on the loopback address")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--mutation", action="append", default=[], metavar="ID")
    serve.add_argument(
        "--open-login", action="store_true", help="accept any credentials (sign-in switched off)"
    )
    snap = commands.add_parser("snapshot", help="write DOM snapshots of all pages")
    snap.add_argument("--out", default="data/dom/shop")
    snap.add_argument("--mutation", action="append", default=[], metavar="ID")
    commands.add_parser("list", help="list the mutation catalogue")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            for mutation in CATALOGUE:
                print(f"{mutation.mutation_id}  {mutation.description}")
        elif args.command == "snapshot":
            for path in write_snapshots(args.out, args.mutation):
                print(path)
        else:
            with ShopServer(args.mutation, port=args.port, open_login=args.open_login) as shop:
                print(f"Demo shop at {shop.url}; log in as {DEMO_USER} / {DEMO_PASSWORD}")
                print("Press Ctrl+C to stop it")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
    except (KeyError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
