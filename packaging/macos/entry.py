"""Freeze the shared CLI without importing packaging-only dependencies."""
from tinybuilder.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
