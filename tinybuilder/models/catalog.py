"""Immutable model metadata; qualification is separate from byte verification."""
from dataclasses import dataclass
import re
from urllib.parse import urlsplit


@dataclass(frozen=True)
class CatalogEntry:
    model_id: str
    revision: str
    size_bytes: int
    sha256: str
    license: str
    filename: str
    source_url: str
    qualification: str = "provisional"

    def __post_init__(self):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", self.model_id):
            raise ValueError("Invalid model ID")
        if not re.fullmatch(r"[0-9a-f]{40}", self.revision):
            raise ValueError("An immutable commit revision is required")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("Invalid SHA-256")
        if type(self.size_bytes) is not int or self.size_bytes < 8:
            raise ValueError("Invalid model length")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.gguf", self.filename):
            raise ValueError("Invalid portable GGUF filename")
        if self.filename.split(".")[0].upper() in {
            "CON", "PRN", "AUX", "NUL", *("COM%d" % n for n in range(1, 10)),
            *("LPT%d" % n for n in range(1, 10))
        }:
            raise ValueError("Reserved filename")
        url = urlsplit(self.source_url)
        if (url.scheme not in {"https", "http"} or not url.hostname or
                url.username is not None or url.password is not None or url.fragment or
                self.revision not in url.path.split("/")):
            raise ValueError("A revision-pinned HTTP(S) source is required")
        if not self.license:
            raise ValueError("Model license required")


QWEN_CODER_15B_Q4 = CatalogEntry(
    model_id="qwen2-5-coder-1-5b-instruct-q4-k-m",
    revision="2ab9f8f42af02fc212effaef7c4850c885e965f4",
    size_bytes=1117320768,
    sha256="cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046",
    license="Apache-2.0",
    filename="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
    source_url=("https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/"
                "resolve/2ab9f8f42af02fc212effaef7c4850c885e965f4/"
                "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"),
)
CATALOG = (QWEN_CODER_15B_Q4,)
# No default model: qualification and runtime acceptance are owned elsewhere.
