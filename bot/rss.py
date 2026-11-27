"""Lấy tin từ RSS và tạo bản nháp trong posts/.

Để tránh vi phạm bản quyền, bot KHÔNG chép nguyên văn bài báo hay ảnh của người khác.
Bản nháp chỉ gồm tiêu đề, link nguồn và chỗ để bạn viết tóm tắt bằng lời của mình.
Bản nháp có status: draft, chỉ được đăng khi bạn đổi thành status: approved.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import yaml

from . import config
from .store import State


def slug(text: str, n: int = 40) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"[\s_]+", "-", text).strip("-")[:n] or "tin"


def load_feeds(path: Path = config.FEEDS_FILE) -> list[dict]:
    if not path.exists():
        return []
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("feeds", [])


def fetch(feeds: list[dict], state: State, posts_dir: Path = config.POSTS_DIR,
          parse=feedparser.parse) -> list[Path]:
    created = []
    now = datetime.now(ZoneInfo(config.TIMEZONE)).replace(microsecond=0)
    for feed in feeds:
        parsed = parse(feed["url"])
        for entry in parsed.entries[: feed.get("max_items", 5)]:
            link = entry.get("link")
            key = hashlib.sha1((link or entry.get("id") or entry.get("title", "")).encode()).hexdigest()[:12]
            if not link or state.seen_feed_item(key):
                continue
            title = entry.get("title", "").strip()
            folder = posts_dir / f"tin-{now:%Y%m%d}-{slug(title)}-{key[:4]}"
            folder.mkdir(parents=True, exist_ok=True)
            source = parsed.feed.get("title", feed["url"])
            data = {
                "status": "draft",
                "publish_at": now.isoformat(),
                "platforms": feed.get("platforms", ["facebook", "x"]),
                "text": f"{title}\n\n(Viết 1–3 câu tóm tắt bằng lời của bạn ở đây)\n\nNguồn: {source}",
                "link": link,
                "media": [],
            }
            (folder / "post.yaml").write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            state.mark_feed_item(key)
            created.append(folder)
    return created
