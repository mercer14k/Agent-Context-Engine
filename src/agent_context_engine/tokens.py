"""Counts at a declared boundary, never a claim about a complete provider invoice."""
import hashlib
import os
from pathlib import Path
from typing import Protocol

VOCAB_URL = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
VOCAB_HASH = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"


class Tokenizer(Protocol):
    identity: str
    model_mapping: str
    def count(self, text: str) -> int: ...


class Tiktoken:
    identity = "tiktoken:cl100k_base"
    model_mapping = "encoding only; no asserted model or billing mapping"

    def __init__(self, cache: Path):
        # Check the single supported vocabulary before library loading; no surprise network.
        path = cache / hashlib.sha1(VOCAB_URL.encode()).hexdigest()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != VOCAB_HASH:
            raise ValueError("Tokenizer unavailable; run ace tokenizer-prepare explicitly")
        os.environ["TIKTOKEN_CACHE_DIR"] = str(cache)
        import tiktoken
        self.identity = f"tiktoken:{tiktoken.__version__}:cl100k_base"
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        return len(self.encoding.encode(text, disallowed_special=()))


def available(cache: Path) -> Tokenizer | None:
    try:
        return Tiktoken(cache)
    except (ImportError, ValueError, OSError):
        return None


def prepare(cache: Path) -> None:
    """Explicit one-time public vocabulary download; no prompts are transmitted."""
    from urllib.request import urlopen
    with urlopen(VOCAB_URL, timeout=30) as response:
        data = response.read(8_000_000)
    if hashlib.sha256(data).hexdigest() != VOCAB_HASH:
        raise ValueError("Tokenizer vocabulary integrity failure")
    cache.mkdir(parents=True, exist_ok=True)
    (cache / hashlib.sha1(VOCAB_URL.encode()).hexdigest()).write_bytes(data)
