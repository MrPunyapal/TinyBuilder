"""Opt-in CPU read qualification; no downloads or runtime implementation."""
import argparse
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path

if __package__:
    from .evaluate import main as evaluate
else:
    from evaluate import main as evaluate

CANDIDATES = {
    "qwen2.5-coder-1.5b": (1117320768, "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"),
    "qwen3-4b": (2497280256, "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5"),
}


def verify_model(path, identity):
    size, digest = identity
    if not path.is_file() or path.stat().st_size != size:
        raise ValueError("Model size does not match publisher metadata")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        if stream.read(4) != b"GGUF":
            raise ValueError("Model is not GGUF")
        stream.seek(0)
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != digest:
        raise ValueError("Model hash does not match publisher metadata")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=tuple(CANDIDATES), required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-seed", default=None)
    args = parser.parse_args(argv)
    seed = args.fixture_seed or secrets.token_hex(16)
    if len(seed) != 32 or any(c not in "0123456789abcdefABCDEF" for c in seed):
        parser.error("Fixture seed must be 32 hex characters")
    try:
        verify_model(args.model.resolve(strict=True), CANDIDATES[args.candidate])
        from tinybuilder.runtime import RuntimeManager
    except (OSError, ValueError, ImportError):
        parser.error("Approved model identity or runtime integration unavailable")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {"candidate": args.candidate, "model_bytes": CANDIDATES[args.candidate][0],
              "model_sha256": CANDIDATES[args.candidate][1], "backend": "cpu",
              "trials_requested": 10, "cold_ready_seconds": None,
              "warm_ready_seconds": None, "ttft_seconds": None,
              "tokens_per_second": None, "peak_ram_bytes": None, "peak_vram_bytes": None,
              "evaluation_exit": None, "status": "aborted"}
    try:
        with RuntimeManager(args.runtime.resolve(strict=True)) as runtime:
            connection = runtime.start(args.model.resolve(strict=True), backend="cpu", timeout=180)
            report["cold_ready_seconds"] = round(time.monotonic() - started, 3)
            report["evaluation_exit"] = evaluate([
                "--require-managed", "--smoke-profile", "hidden-facts-v1", "--models",
                connection.model_alias, "--trials", "10", "--fixture-seed", seed,
                "--tool-protocol", "strict-json", "--strict-json-profile", "constrained",
                "--progress-guidance", "checklist", "--max-steps", "8",
                "--output", str(out / "evaluation")], connection=connection)
        report["status"] = "completed"
        return report["evaluation_exit"]
    finally:
        report["duration_seconds"] = round(time.monotonic() - started, 3)
        (out / "campaign.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
