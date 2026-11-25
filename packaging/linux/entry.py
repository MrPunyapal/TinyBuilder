"""Freeze the shared application entry point, not a second application."""
from tinybuilder.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
