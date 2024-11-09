# CLI.py
import argparse
from stokvel import perform_monthly_cycle

def handle_stokvel(args):
    perform_monthly_cycle()  # Call the stokvel function

def main():
    parser = argparse.ArgumentParser(description="Algorand CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Parser for handling the stokvel
    stokvel_parser = subparsers.add_parser("stokvel", help="Run a monthly stokvel cycle")
    stokvel_parser.set_defaults(func=handle_stokvel)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
