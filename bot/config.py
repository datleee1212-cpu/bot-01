"""Đọc cấu hình từ biến môi trường (file .env)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

POSTS_DIR = Path(os.getenv("POSTS_DIR", ROOT / "posts"))
STATE_FILE = Path(os.getenv("STATE_FILE", ROOT / "state.json"))
TOKENS_FILE = Path(os.getenv("TOKENS_FILE", ROOT / ".secrets" / "tokens.json"))
FEEDS_FILE = Path(os.getenv("FEEDS_FILE", ROOT / "config" / "feeds.yaml"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v23.0")


def env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and not value:
        raise RuntimeError(f"Thiếu biến môi trường {name}. Xem .env.example")
    return value


class TokenStore:
    """Lưu token được làm mới tự động (TikTok) vào .secrets/tokens.json."""

    def __init__(self, path: Path = TOKENS_FILE):
        self.path = path

    def load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def get(self, key: str) -> dict:
        return self.load().get(key, {})

    def set(self, key: str, value: dict) -> None:
        data = self.load()
        data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
