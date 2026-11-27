"""Hàng đợi bài viết.

Mỗi bài là một thư mục trong posts/ chứa post.yaml và các file ảnh/video.
Trạng thái đã đăng lưu trong state.json để không đăng trùng.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import config

PLATFORMS = ("facebook", "instagram", "x", "tiktok")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm"}


@dataclass
class Post:
    id: str
    folder: Path
    text: str
    platforms: list[str]
    publish_at: datetime
    status: str = "approved"
    link: str | None = None
    media: list[Path] = field(default_factory=list)
    options: dict = field(default_factory=dict)

    @property
    def images(self) -> list[Path]:
        return [m for m in self.media if m.suffix.lower() in IMAGE_EXT]

    @property
    def videos(self) -> list[Path]:
        return [m for m in self.media if m.suffix.lower() in VIDEO_EXT]

    def text_for(self, platform: str) -> str:
        """Cho phép ghi đè nội dung riêng cho từng nền tảng: text_x, text_facebook..."""
        return self.options.get(f"text_{platform}") or self.text


def _parse_time(value, tz: str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt


def load_post(folder: Path, tz: str = config.TIMEZONE) -> Post:
    raw = yaml.safe_load((folder / "post.yaml").read_text(encoding="utf-8")) or {}
    platforms = raw.get("platforms") or list(PLATFORMS)
    unknown = set(platforms) - set(PLATFORMS)
    if unknown:
        raise ValueError(f"{folder.name}: nền tảng không hỗ trợ {sorted(unknown)}")
    media = [folder / m for m in raw.get("media", [])]
    for m in media:
        if not m.exists():
            raise FileNotFoundError(f"{folder.name}: không thấy file {m.name}")
    known = {"text", "platforms", "publish_at", "status", "link", "media"}
    return Post(
        id=folder.name,
        folder=folder,
        text=(raw.get("text") or "").strip(),
        platforms=platforms,
        publish_at=_parse_time(raw.get("publish_at", datetime.now(ZoneInfo(tz))), tz),
        status=raw.get("status", "approved"),
        link=raw.get("link"),
        media=media,
        options={k: v for k, v in raw.items() if k not in known},
    )


def load_posts(posts_dir: Path = config.POSTS_DIR) -> list[Post]:
    posts = []
    for folder in sorted(p for p in posts_dir.iterdir() if (p / "post.yaml").exists()):
        try:
            posts.append(load_post(folder))
        except Exception as exc:  # một bài lỗi không làm dừng cả hàng đợi
            print(f"[bỏ qua] {exc}")
    return posts


class State:
    def __init__(self, path: Path = config.STATE_FILE):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def done(self, post_id: str, platform: str) -> bool:
        return "id" in self.data.get("posts", {}).get(post_id, {}).get(platform, {})

    def record(self, post_id: str, platform: str, result: dict) -> None:
        self.data.setdefault("posts", {}).setdefault(post_id, {})[platform] = result
        self.save()

    def seen_feed_item(self, key: str) -> bool:
        return key in self.data.get("feed_seen", [])

    def mark_feed_item(self, key: str) -> None:
        self.data.setdefault("feed_seen", []).append(key)
        self.save()

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")


def due_jobs(posts: list[Post], state: State, now: datetime) -> list[tuple[Post, str]]:
    """Các cặp (bài, nền tảng) đã đến giờ, đã duyệt và chưa đăng."""
    jobs = []
    for post in posts:
        if post.status != "approved" or post.publish_at > now:
            continue
        for platform in post.platforms:
            if not state.done(post.id, platform):
                jobs.append((post, platform))
    return jobs
