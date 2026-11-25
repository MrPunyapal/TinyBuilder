"""Upstream-published metadata; not a qualification of extracted binaries."""

REVISION = "b6500"
RELEASE_URL = "https://github.com/ggml-org/llama.cpp/releases/tag/b6500"
# SHA-256 from the official release API, not locally recomputed.
CPU_ARCHIVES = {
    ("windows", "x64"): (
        "llama-b6500-bin-win-cpu-x64.zip",
        "73e00267e852e666a6fce2c3fb7a2603dd1934a37259f3f45c2c1b6983fa605a",
    ),
    ("macos", "arm64"): (
        "llama-b6500-bin-macos-arm64.zip",
        "4f34ae19823ee22e8036d6da91f083ca62ab926c2a0a4a5ce9df34897360087b",
    ),
    ("linux", "x64"): (
        "llama-b6500-bin-ubuntu-x64.zip",
        "716803084e565fe779bc2d01ea576c418be141f8fabac97509bc6d7c3cd786b2",
    ),
}
BACKENDS = frozenset(("cpu", "cuda", "vulkan", "metal", "rocm"))
